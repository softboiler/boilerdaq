"""Data processing pipeline for a nucleate pool boiling apparatus."""

from collections import UserDict, deque
from csv import DictReader, DictWriter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Self

from mcculw.ul import ULError, t_in, v_in
from PyQt5.QtCore import QTimer
from pyqtgraph import (
    GraphicsLayoutWidget,
    PlotCurveItem,
    intColor,
    mkQApp,
    setConfigOptions,
)
from pyvisa import ResourceManager, VisaIOError
from pyvisa.resources import MessageBasedResource
from simple_pid import PID

# * -------------------------------------------------------------------------------- * #

setConfigOptions(antialias=True)
HISTORY_LENGTH = 300  # points to keep for plotting and fitting


class Sensor(NamedTuple):
    """Sensor parameters.

    Parameters
    ----------
    name: str
        Name of the sensor.
    board: int
        Which board the sensor belongs to.
    channel: int
        The channel pointing to this sensor on the board.
    reading: int
        The sensor type, either "Temperature" or "Voltage".
    unit: str
        The unit type for values reported by the board.
    """

    name: str
    board: int
    channel: int
    reading: str
    unit: str

    @classmethod
    def get(cls, path: str) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``Sensor``."""
        sensors = []
        with Path(path).open() as csv_file:
            reader = DictReader(csv_file)
            sensors.extend(
                cls(
                    row["name"],
                    int(row["board"]),
                    int(row["channel"]),
                    row["reading"],
                    row["unit"],
                )
                for row in reader
            )
        return sensors


class ScaledParam(NamedTuple):
    """Parameters for scalar modification of a sensor.

    Parameters
    ----------
    name: str
        Name of the scaled value.
    unscaled_sensor: str
        Name of the sensor to be scaled.
    scale: float
        The scale to apply.
    offset: float
        The offset to apply.
    unit: str
        The unit type after scaling.
    """

    name: str
    unscaled_sensor: str
    scale: float
    offset: float
    unit: str

    @classmethod
    def get(cls, path: str) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ScaledParam``."""
        params = []
        with Path(path).open() as csv_file:
            reader = DictReader(csv_file)
            params.extend(
                cls(
                    row["name"],
                    row["unscaled_sensor"],
                    float(row["scale"]),
                    float(row["offset"]),
                    str(row["unit"]),
                )
                for row in reader
            )
        return params


class FluxParam(NamedTuple):
    """Parameters for the flux between two sensors.

    Parameters
    ----------
    name: str
        The name of the flux.
    origin_sensor: str
        The name of the sensor at the origin.
    distant_sensor: str
        The name of the sensor not at the origin.
    conductivity: float
        The conductivity of the path between the sensors.
    length: float
        The length of the path between the sensors.
    unit: str
        The unit type of the flux.
    """

    name: str
    origin_sensor: str
    distant_sensor: str
    conductivity: float
    length: float
    unit: str

    @classmethod
    def get(cls, path: str) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``FluxParam``."""
        params = []
        with Path(path).open() as csv_file:
            reader = DictReader(csv_file)
            params.extend(
                cls(
                    row["name"],
                    row["origin_sensor"],
                    row["distant_sensor"],
                    float(row["conductivity"]),
                    float(row["length"]),
                    row["unit"],
                )
                for row in reader
            )
        return params


class ExtrapParam(NamedTuple):
    """Parameters for extrapolation from two sensors and a flux to a point of interest.

    Parameters
    ----------
    name: str
        The name of the extrapolation.
    origin_sensor: str
        The name of the sensor at the origin.
    distant_sensor: str
        The name of the sensor not at the origin.
    conductivity: float
        The conductivity of the path from ``distant_sensor`` to the point of interest.
    length: float
        The length of the path from ``distant_sensor`` to the point of interest.
    unit: str
        The unit type of the extrapolation.
    """

    name: str
    origin_sensor: str
    flux: str
    conductivity: float
    length: float
    unit: str

    @classmethod
    def get(cls, path: str) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ExtrapParam``."""
        params = []
        with Path(path).open() as csv_file:
            reader = DictReader(csv_file)
            params.extend(
                cls(
                    row["name"],
                    row["origin_sensor"],
                    row["flux"],
                    float(row["conductivity"]),
                    float(row["length"]),
                    row["unit"],
                )
                for row in reader
            )
        return params


class PowerParam(NamedTuple):
    """Parameters for power supplies.

    Parameters
    ----------
    name: str
        The name of the power supply parameter.
    unit:
        The unit of the power supply parameter.
    """

    name: str
    unit: str

    @classmethod
    def get(cls, path: str) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ExtrapParam``."""
        power_supplies = []
        with Path(path).open() as csv_file:
            reader = DictReader(csv_file)
            power_supplies.extend(
                cls(
                    row["name"],
                    row["unit"],
                )
                for row in reader
            )
        return power_supplies


class Result:
    """A result.

    Attributes:
    ----------
    source: str
        The source of the result.
    value: float
        The value of the result.
    time: float
        The time that the result was taken, with the oldest result at zero.
    history: Deque[float]
        Previous values resulting from the source.
    """

    def __init__(self):
        self.source: Sensor = None  # type: ignore
        self.value: float = None  # type: ignore
        self.history: deque[float] = deque(
            [0.0] * HISTORY_LENGTH, maxlen=HISTORY_LENGTH
        )

    def update(self):
        """Update the result."""
        self.history.append(self.value)


def get_result(name: str, results: list[Result]) -> Result:
    """Get a result or results by the source name."""
    result_names = [result.source.name for result in results]
    i = result_names.index(name)
    return results[i]


UNIT_TYPES = {"C": 0, "F": 1, "K": 2, "V": 5}


class Reading(Result):
    """A reading directly from a sensor.

    Parameters
    ----------
    sensor: Sensor
        The sensor parameters used to get a result.

    Attributes:
    ----------
    unit_types: Dict[str: int]
        Enumeration of unit types supported by the board on which the sensor resides.
    """

    def __init__(self, sensor: Sensor):
        super().__init__()
        self.source = sensor

    def update(self):
        """Update the result."""
        if self.source.reading == "temperature":
            try:
                unit_int = UNIT_TYPES[self.source.unit]
                self.value = t_in(self.source.board, self.source.channel, unit_int)
            except ULError:  # type: ignore
                self.value = 0
        elif self.source.reading == "voltage":
            self.value = v_in(self.source.board, self.source.channel, 0)
        super().update()


class ScaledResult(Result):
    """A scaled result.

    Parameters
    ----------
    scaled_param: ScaledParam
        The parameters for obtaining a scaled result.
    results: List[Result]
        A list of results containing the source to be scaled.

    Attributes:
    ----------
    unscaled_result: Result
        The unscaled result.
    """

    def __init__(
        self,
        scaled_param: ScaledParam,
        results: list[Result],
    ):
        super().__init__()
        self.source: ScaledParam = scaled_param  # type: ignore
        self.unscaled_result = get_result(scaled_param.unscaled_sensor, results)

    def update(self):
        """Update the result."""
        self.value = self.unscaled_result.value * self.source.scale + self.source.offset  # type: ignore
        super().update()


class Flux(Result):
    """A flux result.

    Parameters
    ----------
    flux_param: FluxParam
        The parameters for obtaining a flux result.
    results: List[Result]
        A list of results containing the source to be scaled.

    Attributes:
    ----------
    origin_result: Result
        The result of the source at the origin.
    distant_result: Result
        The result of the source not at the origin.
    """

    def __init__(
        self,
        flux_param: FluxParam,
        results: list[Result],
    ):
        super().__init__()
        self.source: FluxParam = flux_param  # type: ignore
        self.origin_result = get_result(flux_param.origin_sensor, results)
        self.distant_result = get_result(flux_param.distant_sensor, results)

    def update(self):
        """Update the result."""
        self.value = (
            self.source.conductivity
            / self.source.length
            * (self.origin_result.value - self.distant_result.value)  # type: ignore
        )
        super().update()


class ExtrapResult(Result):
    """An extrapolated result.

    Parameters
    ----------
    extrap_param: ExtrapParam
        The parameters for obtaining an extrapolated result.
    results: List[Result]
        A list of results containing the source to be scaled.

    Attributes:
    ----------
    origin_result: Result
        The result of the source at the origin.
    distant_result: Result
        The result of the source not at the origin.
    """

    def __init__(
        self,
        extrap_param: ExtrapParam,
        results: list[Result],
    ):
        super().__init__()
        self.source: ExtrapParam = extrap_param  # type: ignore
        self.origin_result = get_result(extrap_param.origin_sensor, results)
        self.flux_result = get_result(extrap_param.flux, results)

    def update(self):
        """Update the result."""
        self.value = self.origin_result.value - (
            self.flux_result.value * self.source.length / self.source.conductivity
        )
        super().update()


class PowerResult(Result):
    """A result from a power supply.

    Parameters
    ----------
    power_param: PowerParam
        The parameters for obtaining a result from the power supply.
    instrument
        The VISA instrument from which to obtain the result.
    current_limit: float
        The current limit to be set.
    """

    def __init__(
        self,
        power_param: PowerParam,
        instrument: str,
        current_limit: float,
    ):
        self.source: PowerParam = power_param  # type: ignore
        self.resource_manager = ResourceManager()
        self.instrument_name: str = instrument
        self.instrument: MessageBasedResource | None = None  # type: ignore
        self.current_limit = current_limit

    def open(self):  # noqa: A003
        """Open the instrument."""
        self.instrument = self.resource_manager.open_resource(  # type: ignore
            self.instrument_name,
            read_termination="\n",
            write_termination="\n",
        )
        self.instrument.write("output:state on")  # type: ignore
        self.instrument.write(f"source:current {self.current_limit}")  # type: ignore

    def close(self):
        """Close the instrument."""
        if not self.instrument:
            return
        self.instrument.write("output:state off")  # type: ignore
        self.instrument.close()  # type: ignore
        self.instrument = None

    def one_shot(self):
        """Take a single measurement."""
        self.open()
        self.close()

    def update(self):
        """Update the result."""
        try:
            if self.source.name == "V":
                self.value = float(self.instrument.query("measure:voltage?"))  # type: ignore
            elif self.source.name == "I":
                self.value = float(self.instrument.query("measure:current?"))  # type: ignore
        except VisaIOError as exc:
            print(exc)

    def write(self, value):
        """Write a value back to the instrument."""
        try:
            if self.source.name == "V":
                self.instrument.write(f"source:voltage {value!s}")  # type: ignore
            elif self.source.name == "I":
                self.instrument.write(f"source:current {value!s}")  # type: ignore
        except VisaIOError as exc:
            print(exc)


class ResultGroup(UserDict[str, list[Result]]):
    """A group of results.

    Parameters
    ----------
    group_dict
        Dictionary of result groupings.
    results: List[Result]
        List of results containing the results to be grouped.
    """

    def __init__(self, group_dict: dict[str, str], results: list[Result]):
        super().__init__()
        for key, val in group_dict.items():
            result_names = val.split()
            filtered_results = []
            for name in result_names:
                result = get_result(name, results)
                filtered_results.append(result)
            self[key] = filtered_results  # type: ignore


class Controller:
    """A PID controller.

    Parameters
    ----------
    control_result: PowerResult
        The result to control based on feedback.
    feedback_result: Result
        The result to get feedback from.
    setpoint: float
        The value that the feedback should be coerced to through PID control.
    gains: List[float]
        List of the proportional, integral, and derivative gains of the PID controller.
    output_limits: Tuple[float, float]
        Limits of the PID controller.
    start_delay: float
        Time to wait before activating PID.

    Attributes:
    ----------
    pid: PID
        The PID controller.
    """

    def __init__(
        self,
        control_result: PowerResult,
        feedback_result: Result,
        setpoint: float,
        gains: tuple[float, float, float],
        output_limits: tuple[float, float],
    ):
        self.control_result: PowerResult = control_result
        self.feedback_result: Result = feedback_result
        self.pid = PID(
            *gains,
            setpoint,
            output_limits=output_limits,
            starting_output=self.control_result.value,
        )
        self.feedback_value = self.feedback_result.value

    def open(self):  # noqa: A003
        """Open the instrument to be controlled."""
        self.control_result.open()

    def close(self):
        """Close the instrument to be controlled."""
        self.control_result.close()

    def update(self):
        """Update the PID controller."""
        self.feedback_value = self.feedback_result.value
        control_value = self.pid(self.feedback_value)
        print(f"{self.feedback_value} {control_value}")
        self.control_result.write(control_value)


class Writer:
    """A CSV file writer.

    Parameters
    ----------
    path: str
        Base name of the first results CSV to be written (e.g. `results.csv`). The ISO
        time of creation of the file will be appended to the provided path (e.g.
        `results_yyyy_mm_ddThh-mm-ss.csv`).
    results: List[Result]
        The first list of results to be written to a file.

    Attributes:
    ----------
    paths: List[str]
        Base names of multiple results CSVs to be written to.
    result_groups: List[List[Result]]
        Groups of results to be written to each of the names in `paths`.
    fieldname_groups: List[str]
        Groups of fieldnames to be written to each of the names in `paths`.
    time: datetime
        The time that the last value was taken.
    """

    def __init__(
        self,
        path: str,
        results: list[Result],
    ):
        self.paths: list[str] = []
        self.result_groups: list[list[Result]] = []
        self.fieldname_groups: list[list[str]] = []
        self.time: datetime = datetime.now()  # type: ignore
        self.add(path, results)

    def add(self, path: str, results: list[Result]):
        """Add a CSV file to be written to and a set of results to write to it.

        Parameters
        ----------
        path: str
            Base name of additional results CSVs to be written (e.g. `results.csv`). The
            ISO time of creation of the file will be appended to the provided path (e.g.
            `results_yyyy_mm_ddThh-mm-ss.csv`).
        results: List[Result]
            Additonal list of results to be written to a file.
        """

        # The ":" in ISO time strings is not supported by filenames
        file_time = self.time.isoformat(timespec="seconds").replace(":", "-")  # type: ignore
        path = Path(path)  # type: ignore
        path = str(path.with_name(f"{path.name}_{file_time}"))  # type: ignore
        # Compose the fieldnames and first row of values
        sources = [f"{result.source.name} ({result.source.unit})" for result in results]
        fieldnames = ["time", *sources]
        for result in results:
            if isinstance(result, PowerResult):
                result.open()
            result.update()
        values = [self.time.isoformat()] + [result.value for result in results]  # type: ignore
        to_write = dict(zip(fieldnames, values, strict=True))

        # Create the CSV, writing the header and the first row of values
        with Path(path).open("w", newline="") as csv_file:
            csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerow(to_write)

        # Record the file and results for writing additional rows later.
        self.paths.append(path)
        self.result_groups.append(results)
        self.fieldname_groups.append(fieldnames)

    def update(self):
        """Update results and write the new data to CSV."""
        self.time: str = datetime.now().isoformat()
        for results in self.result_groups:
            for result in results:
                result.update()
        self.write()

    def write(self):
        """Write data to CSV."""
        for path, results, fieldnames in zip(
            self.paths, self.result_groups, self.fieldname_groups, strict=True
        ):
            values = [self.time] + [result.value for result in results]
            to_write = dict(zip(fieldnames, values, strict=True))

            with Path(path).open("a", newline="") as csv_file:
                csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
                csv_writer.writerow(to_write)


class Plotter:
    """A plotter for data.

    Parameters
    ----------
    title: str
        The title of the first plot.
    results: List[Result]
        The results to plot.
    row: int = 0
        The window row to place the first plot.
    col: int = 0
        The window column to place the first plot.

    Attributes:
    ----------
    all_results: List[Result]
    all_curves: List[PlotCurveItem]
    all_histories: List[Deque]
    time: List[int]
    """

    def __init__(
        self,
        title: str,
        results: list[Result],
        row: int = 0,
        col: int = 0,
    ):
        self.window = GraphicsLayoutWidget()
        self.all_results: list[Result] = []
        self.all_curves: list[PlotCurveItem] = []
        self.all_histories: list[deque[float]] = []
        self.time: list[int] = [-i for i in range(HISTORY_LENGTH)]
        self.time.reverse()
        self.add(title, results, row, col)

    def add(self, title: str, results: list[Result], row: int, col: int):
        """Plot results to a new pane in the plot window.

        Parameters
        ----------
        title: str
            The title of an additional plot.
        results: List[Result]
            The results to plot.
        row: int = 0
            The window row to place an additional plot.
        col: int = 0
            The window column to place an additional plot.
        """
        plot = self.window.addPlot(row, col)
        plot.addLegend()
        plot.setLabel("left", units=results[0].source.unit)
        plot.setLabel("bottom", units="s")
        plot.setTitle(title)
        self.all_results.extend(results)
        histories = [result.history for result in results]
        self.all_histories.extend(histories)
        names = [result.source.name for result in results]
        for i, (history, name) in enumerate(zip(histories, names, strict=True)):
            curve = plot.plot(self.time, history, pen=intColor(i), name=name)
            self.all_curves.append(curve)

    def update(self):
        """Update plots."""
        for curve, history in zip(self.all_curves, self.all_histories, strict=True):
            curve.setData(self.time, history)


class Looper:
    """Handles threads for plotting, writing, and control.

    Parameters
    ----------
    writer: Writer
        The writer.
    plotter: Plotter
        The plotter.
    controller: Optional[Controller]
        The controller.

    Attributes:
    ----------
    plot_window_open: bool
        Whether the plot window is currently open.
    """

    def __init__(
        self, writer: Writer, plotter: Plotter, controller: Controller | None = None
    ):
        self.app = mkQApp()
        self.writer = writer
        self.plotter = plotter
        self.controller = controller or None

    def start(self):
        """Start the write/control thread and plot on the main thread."""
        if self.controller:
            self.controller.open()
        timer = QTimer()
        timer.timeout.connect(self.plot_control if self.controller else self.plot)
        timer.start(100)
        self.plotter.window.show()
        self.app.exec_()
        self.app.quit()
        if self.controller:
            self.controller.close()

    def plot(self):
        """The function to be looped in the plot thread."""
        self.plotter.update()
        self.writer.update()

    def plot_control(self):
        """The CSV writer function to be looped in the write/control thread."""
        self.plotter.update()
        self.writer.update()
        self.controller.update()  # type: ignore
