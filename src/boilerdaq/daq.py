"""Data acquisition functions."""

from collections import UserDict, deque
from contextlib import suppress
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import Any, NamedTuple, Self
from warnings import warn

from boilercore.fits import fit_from_params
from boilercore.modelfun import get_model
from boilercore.models.fit import Fit
from boilercore.models.geometry import GEOMETRY
from boilercore.types import Rod
from pyqtgraph import (
    DateAxisItem,
    GraphicsLayoutWidget,
    PlotCurveItem,
    intColor,
    mkQApp,
    setConfigOptions,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from pyvisa import ResourceManager, VisaIOError
from pyvisa.resources import MessageBasedResource
from simple_pid import PID

try:
    try:
        from mcculw.enums import InterfaceType
        from mcculw.ul import ULError, get_daq_device_inventory, t_in, v_in
    except NameError:
        from uldaq import InterfaceType, get_daq_device_inventory

        from boilerdaq.shim import t_in, v_in

    if not get_daq_device_inventory(InterfaceType.USB):  # pyright: ignore[reportArgumentType]
        from boilerdaq.dummy import t_in, v_in
except FileNotFoundError:
    from boilerdaq.dummy import t_in, v_in


setConfigOptions(antialias=True)

PLOT_HISTORY_DURATION = 5  # (min)
"""Duration of plot history."""
POLLING_INTERVAL = 2000
"""Minimum time between sampling cycles in milliseconds."""
PLOT_HISTORY_LENGTH = PLOT_HISTORY_DURATION * 60 * 1000 // POLLING_INTERVAL
"""Length of plot history in number of samples."""


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
    def get(cls, path: Path) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``Sensor``."""
        sensors = []
        with path.open(encoding="utf-8") as csv_file:
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


class Param(NamedTuple):
    """A generic parameter.

    Parameters
    ----------
    name: str
        The name of the parameter.
    unit:
        The unit of the parameter.
    """

    name: str
    unit: str


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
    def get(cls, path: Path) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ScaledParam``."""
        params = []
        with path.open(encoding="utf-8") as csv_file:
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
    def get(cls, path: Path) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``FluxParam``."""
        params = []
        with path.open(encoding="utf-8") as csv_file:
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
    def get(cls, path: Path) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ExtrapParam``."""
        params = []
        with path.open(encoding="utf-8") as csv_file:
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
    def get(cls, path: Path) -> list[Self]:
        """Process a CSV file at ``path``, returning a ``List`` of ``PowerParam``."""
        power_supplies = []
        with path.open(encoding="utf-8") as csv_file:
            reader = DictReader(csv_file)
            power_supplies.extend(cls(row["name"], row["unit"]) for row in reader)
        return power_supplies


class Result:
    """A result.

    Attributes
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
        self.history: deque[float] = deque(maxlen=PLOT_HISTORY_LENGTH)

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

    Attributes
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

    Attributes
    ----------
    unscaled_result: Result
        The unscaled result.
    """

    def __init__(self, scaled_param: ScaledParam, results: list[Result]):
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

    Attributes
    ----------
    origin_result: Result
        The result of the source at the origin.
    distant_result: Result
        The result of the source not at the origin.
    """

    def __init__(self, flux_param: FluxParam, results: list[Result]):
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

    Attributes
    ----------
    origin_result: Result
        The result of the source at the origin.
    distant_result: Result
        The result of the source not at the origin.
    """

    def __init__(self, extrap_param: ExtrapParam, results: list[Result]):
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


class FitResult(Result):
    """A result from a model fit."""

    def __init__(
        self,
        name: str,
        unit: str,
        fit: Fit,
        models: Path,
        results_to_fit: list[Result],
        rod: Rod = "R",
    ):
        super().__init__()
        self.name = name
        self.unit = unit
        self.fit = fit
        self.source = Param(name, unit)  # type: ignore
        self.results_to_fit = results_to_fit
        self.model, _ = get_model(models)
        self.x = GEOMETRY.rods[rod]

    def update(self):
        """Update the result."""
        fits, _errors = fit_from_params(
            model=self.model,
            params=self.fit,
            x=self.x,
            y=[result.value for result in self.results_to_fit],
        )
        self.value = fits[self.name]
        super().update()


def open_instrument(name: str) -> MessageBasedResource:
    """Open an instrument by name, falling back to a simulated instrument."""
    rm = ResourceManager()
    if rm.list_resources(name):
        return rm.open_resource(name, read_termination="\n", write_termination="\n")  # pyright: ignore[reportReturnType]
    with NamedTemporaryFile(encoding="utf-8", mode="w", delete=False) as f:
        # sourcery skip: extract-method
        f.write(
            dedent(rf"""
                spec: "1.0"
                devices:
                    device:
                        eom:
                            USB INSTR:
                                q: "\n"
                                r: "\n"
                        dialogues:
                            - q: "measure:voltage?"
                              r: "1"
                            - q: "measure:current?"
                              r: "1"
                resources:
                    {name}:
                        device: "device"
                """).strip()
            + "\n"
        )
        f.close()
        path = Path(f.name)
        inst = ResourceManager(f"{path.as_posix()}@sim").open_resource(
            name, read_termination="\n", write_termination="\n"
        )
        path.unlink()
        return inst  # pyright: ignore[reportReturnType]


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

    def __init__(self, power_param: PowerParam, instrument: str, current_limit: float):
        super().__init__()
        self.source: PowerParam = power_param  # type: ignore
        self.instrument_name: str = instrument
        self.instrument: MessageBasedResource | None = None  # type: ignore
        self.current_limit = current_limit

    def open(self):
        """Open the instrument."""
        self.instrument = open_instrument(self.instrument_name)
        self.instrument.write("output:state on")  # type: ignore
        self.instrument.write(f"source:current {self.current_limit}")

    def close(self):
        """Close the instrument."""
        if not self.instrument:
            return
        # We don't actually write zero here because the PID will get `starting_output`
        # by querying voltage next time the supply is turned on.
        self.instrument.write("output:state off")  # type: ignore
        self.instrument.close()  # type: ignore
        self.instrument = None

    def one_shot(self):
        """Take a single measurement."""
        self.open()
        self.update()
        self.close()

    def update(self):
        """Update the result."""
        try:
            if self.source.name == "V":
                self.value = float(self.instrument.query("measure:voltage?"))  # type: ignore
            elif self.source.name == "I":
                self.value = float(self.instrument.query("measure:current?"))  # type: ignore
        except VisaIOError as exc:
            warn(str(exc), stacklevel=2)
        super().update()

    def write(self, value):
        """Write a value back to the instrument."""
        try:
            if self.source.name == "V":
                self.instrument.write(f"source:voltage {value!s}")  # type: ignore
            elif self.source.name == "I":
                self.instrument.write(f"source:current {value!s}")  # type: ignore
        except VisaIOError as exc:
            warn(str(exc), stacklevel=2)


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
    control_result: Result
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

    Attributes
    ----------
    pid: PID
        The PID controller.
    """

    def __init__(
        self,
        control_result: Result,
        feedback_result: Result,
        setpoint: float,
        gains: tuple[float, float, float],
        output_limits: tuple[float, float],
    ):
        self.control_result: PowerResult = control_result  # type: ignore
        self.feedback_result: Result = feedback_result
        self.pid = PID(
            *gains,
            setpoint=setpoint,
            sample_time=None,  # Controlled by POLLING_INTERVAL
            output_limits=output_limits,
            starting_output=self.control_result.value,
        )
        self.feedback_value = self.feedback_result.value

    def start(self):
        """Start the controller."""
        self.control_result.open()

    def close(self):
        """Close the instrument to be controlled."""
        self.control_result.close()

    def update(self):
        """Update the PID controller."""
        self.feedback_value = self.feedback_result.value
        control_value = self.pid(self.feedback_value)
        self.control_result.write(control_value)


class Writer:
    """A CSV file writer.

    Parameters
    ----------
    path: Path
        Base name of the first results CSV to be written (e.g. `results.csv`). The ISO
        time of creation of the file will be appended to the provided path (e.g.
        `results_yyyy_mm_ddThh-mm-ss.csv`).
    results: List[Result]
        The first list of results to be written to a file.

    Attributes
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

    def __init__(self, path: Path, results: list[Result]):
        self.paths: list[Path] = []
        self.results: list[Any] = []
        self.result_groups: list[list[Result]] = []
        self.fieldname_groups: list[list[str]] = []
        self.time: datetime = datetime.now()  # type: ignore
        self.add(path, results)

    def add(self, path: Path, results: list[Result]):
        """Add a CSV file to be written to and a set of results to write to it.

        Parameters
        ----------
        path: Path
            Base name of additional results CSVs to be written (e.g. `results.csv`). The
            ISO time of creation of the file will be appended to the provided path (e.g.
            `results_yyyy_mm_ddThh-mm-ss.csv`).
        results: List[Result]
            Additonal list of results to be written to a file.
        """
        # The ":" in ISO time strings is not supported by filenames
        file_time = self.time.isoformat(timespec="seconds").replace(":", "-")  # type: ignore
        path = path.with_stem(f"{path.name}_{file_time}")
        # Compose the fieldnames and first row of values
        sources = [f"{result.source.name} ({result.source.unit})" for result in results]
        fieldnames = ["time", *sources]
        for result in results:
            if isinstance(result, PowerResult):
                result.one_shot()
            else:
                result.update()
            with suppress(AttributeError):
                result.history.extend([result.value] * (PLOT_HISTORY_LENGTH - 1))
        values = [self.time.isoformat()] + [result.value for result in results]  # type: ignore
        to_write = dict(zip(fieldnames, values, strict=True))

        # Create the CSV, writing the header and the first row of values
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerow(to_write)

        # Record the file and results for writing additional rows later.
        self.paths.append(path)
        self.results.extend(results)
        self.result_groups.append(results)
        self.fieldname_groups.append(fieldnames)

    def start(self):
        """Start the writer."""
        for result in self.results:
            if isinstance(result, PowerResult):
                result.open()

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

            with path.open("a", newline="", encoding="utf-8") as csv_file:
                csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
                csv_writer.writerow(to_write)


class GraphicsLayoutWidgetWithKeySignal(GraphicsLayoutWidget):
    """Emit key signals on `key_signal`."""

    key_signal = Signal(QKeyEvent)

    def keyPressEvent(self, ev: QKeyEvent):  # noqa: N802
        """Handle keypresses."""
        super().keyPressEvent(ev)
        self.key_signal.emit(ev)


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

    Attributes
    ----------
    all_results: List[Result]
    all_curves: List[PlotCurveItem]
    all_histories: List[Deque]
    time: List[int]
    """

    def __init__(self, title: str, results: list[Result], row: int = 0, col: int = 0):
        self.window = GraphicsLayoutWidgetWithKeySignal()
        self.app = mkQApp()
        self.window.key_signal.connect(self.keyPressEvent)
        self.all_results: list[Result] = []
        self.all_curves: list[PlotCurveItem] = []
        self.all_histories: list[deque[float]] = []
        self.time: deque[float] = deque(maxlen=PLOT_HISTORY_LENGTH)
        current_time = datetime.now()
        self.time.extendleft(
            (current_time - i * timedelta(milliseconds=POLLING_INTERVAL)).timestamp()
            for i in range(PLOT_HISTORY_LENGTH)
        )
        self.add(title, results, row, col)

    def keyPressEvent(self, ev: QKeyEvent):  # noqa: N802
        """Handle quit events and propagate keypresses to image views."""
        if ev.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q, Qt.Key.Key_Enter):
            self.app.closeAllWindows()
            ev.accept()

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
        plot.setAxisItems({"bottom": DateAxisItem()})
        plot.setLabel("left", units=results[0].source.unit)
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
        self.time.append(datetime.now().timestamp())
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

    Attributes
    ----------
    plot_window_open: bool
        Whether the plot window is currently open.
    """

    def __init__(
        self, writer: Writer, plotter: Plotter, controller: Controller | None = None
    ):
        self.writer = writer
        self.plotter = plotter
        self.controller: Controller = controller or None  # type: ignore

    def start(self):
        """Start the write/control thread and plot on the main thread."""
        self.writer.start()
        if self.controller:
            self.controller.start()
        timer = QTimer()
        timer.timeout.connect(self.plot_control if self.controller else self.plot)
        timer.start(POLLING_INTERVAL)
        self.plotter.window.show()
        self.plotter.app.exec()
        self.plotter.app.quit()
        if self.controller:
            self.controller.close()

    def plot(self):
        """Plot function."""
        self.plotter.update()
        self.writer.update()

    def plot_control(self):
        """Plot and control."""
        self.plotter.update()
        self.writer.update()
        self.controller.update()
