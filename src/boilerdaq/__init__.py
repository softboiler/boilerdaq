"""Data processing pipeline for a nucleate pool boiling apparatus."""

from __future__ import annotations

import os
from collections import OrderedDict, deque
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from os.path import splitext
from threading import Thread
from time import sleep
from typing import Deque, List, NamedTuple, Optional, Tuple

import pyqtgraph
from mcculw.ul import ULError, t_in, v_in
from numpy import exp, random
from pyvisa import VisaIOError
from simple_pid import PID

pyqtgraph.setConfigOptions(antialias=True)
DELAY = 2  # read/write/plot timestep
HISTORY_LENGTH = 300  # points to keep for plotting and fitting

DEBUG = os.environ.get("BOILERDAQ_DEBUG") == "True"
if DEBUG:
    DELAY_DEBUG = 0.2
    GAIN_DEBUG = 100
    TAU_DEBUG = DELAY * HISTORY_LENGTH
    NOISE_SCALE = 1e-2


class Sensor(NamedTuple):
    """
    Sensor parameters.

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
    def get(cls, path: str) -> List[Sensor]:
        """Process a CSV file at ``path``, returning a ``List`` of ``Sensor``."""

        sensors = []
        with open(path) as csv_file:
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
    """
    Parameters for scalar modification of a sensor.

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
    def get(cls, path: str) -> List[ScaledParam]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ScaledParam``."""

        params = []
        with open(path) as csv_file:
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
    """
    Parameters for the flux between two sensors.

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
    def get(cls, path: str) -> List[FluxParam]:
        """Process a CSV file at ``path``, returning a ``List`` of ``FluxParam``."""

        params = []
        with open(path) as csv_file:
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
    """
    Parameters for extrapolation from two sensors and a flux to a point of interest.

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
    def get(cls, path: str) -> List[ExtrapParam]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ExtrapParam``."""

        params = []
        with open(path) as csv_file:
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
    """
    Parameters for power supplies.

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
    def get(cls, path: str) -> List[PowerParam]:
        """Process a CSV file at ``path``, returning a ``List`` of ``ExtrapParam``."""

        power_supplies = []
        with open(path) as csv_file:
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
    """
    A result.

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
        self.source = None
        self.value = None
        self.time = deque([], maxlen=HISTORY_LENGTH)
        self.history = deque([], maxlen=HISTORY_LENGTH)
        for _ in range(HISTORY_LENGTH):
            self.time.append(0)
            self.history.append(0)

    def update(self):
        """Update the result."""

        self.history.append(self.value)
        self.time.append(self.time[-1] + DELAY)

    @staticmethod
    def get(name: str, results: List[Result]) -> Result:
        """Get a result or results by the source name."""

        result_names = [result.source.name for result in results]
        i = result_names.index(name)
        return results[i]


class Reading(Result):
    """
    A reading directly from a sensor.

    Parameters
    ----------
    sensor: Sensor
        The sensor parameters used to get a result.

    Attributes
    ----------
    unit_types: Dict[str: int]
        Enumeration of unit types supported by the board on which the sensor resides.
    debug_offset: float
        A random offset to use when debugging.
    """

    unit_types = {"C": 0, "F": 1, "K": 2, "V": 5}

    def __init__(self, sensor: Sensor):
        super().__init__()
        if DEBUG:
            self.debug_offset = random.normal(scale=GAIN_DEBUG)
        self.source = sensor
        self.update()

    def update(self):
        """Update the result."""

        if DEBUG:
            self.value = (
                self.debug_offset
                + GAIN_DEBUG * (1 - exp(-self.time[-1] / TAU_DEBUG))
                + random.normal(scale=NOISE_SCALE * GAIN_DEBUG)
            )
        elif self.source.reading == "temperature":
            try:
                unit_int = self.unit_types[self.source.unit]
                self.value = t_in(self.source.board, self.source.channel, unit_int)
            except ULError:
                self.value = 0
        elif self.source.reading == "voltage":
            self.value = v_in(self.source.board, self.source.channel, 0)
        super().update()


class ScaledResult(Result):
    """
    A scaled result.

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

    def __init__(
        self,
        scaled_param: ScaledParam,
        results: List[Result],
    ):
        super().__init__()
        self.source = scaled_param
        self.unscaled_result = Result.get(scaled_param.unscaled_sensor, results)
        self.update()

    def update(self):
        """Update the result."""

        self.value = self.unscaled_result.value * self.source.scale + self.source.offset
        super().update()


class Flux(Result):
    """
    A flux result.

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

    def __init__(
        self,
        flux_param: FluxParam,
        results: List[Result],
    ):
        super().__init__()
        self.source = flux_param
        self.origin_result = Result.get(flux_param.origin_sensor, results)
        self.distant_result = Result.get(flux_param.distant_sensor, results)
        self.update()

    def update(self):
        """Update the result."""

        self.value = (
            self.source.conductivity
            / self.source.length
            * (self.origin_result.value - self.distant_result.value)
        )
        super().update()


class ExtrapResult(Result):
    """
    An extrapolated result.

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

    def __init__(
        self,
        extrap_param: ExtrapParam,
        results: List[Result],
    ):
        super().__init__()
        self.source = extrap_param
        self.origin_result = Result.get(extrap_param.origin_sensor, results)
        self.flux_result = Result.get(extrap_param.flux, results)

        self.update()

    def update(self):
        """Update the result."""

        self.value = self.origin_result.value - (
            self.flux_result.value * self.source.length / self.source.conductivity
        )
        super().update()


class PowerResult(Result):
    """
    A result from a power supply.

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
        instrument,
        current_limit: float,
    ):
        self.source = power_param
        self.instrument = instrument
        if self.source.name == "V":
            self.instrument.write("output:state on")
            self.instrument.write(f"source:current {current_limit}")
        self.update()

    def update(self):
        """Update the result."""

        try:
            if self.source.name == "V":
                self.value = float(self.instrument.query("measure:voltage?"))
            elif self.source.name == "I":
                self.value = float(self.instrument.query("measure:current?"))
        except VisaIOError as exc:
            print(exc)

    def write(self, value):
        """Write a value back to the instrument."""

        try:
            if self.source.name == "V":
                self.instrument.write(f"source:voltage {str(value)}")
            elif self.source.name == "I":
                self.instrument.write(f"source:current {str(value)}")
        except VisaIOError as exc:
            print(exc)


class ResultGroup(OrderedDict):
    """
    A group of results.

    Parameters
    ----------
    group_dict
        Dictionary of result groupings.
    results: List[Result]
        List of results containing the results to be grouped.
    """

    def __init__(self, group_dict: OrderedDict, results: List[Result]):
        for key, val in group_dict.items():
            result_names = val.split()
            filtered_results = []
            for name in result_names:
                result = Result.get(name, results)
                filtered_results.append(result)
            self[key] = filtered_results


class Controller:
    """
    A PID controller.

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

    Attributes
    ----------
    pid: PID
        The PID controller.
    start_time
        The time that the controller was created.
    """

    def __init__(
        self,
        control_result: PowerResult,
        feedback_result: Result,
        setpoint: float,
        gains: List[float],
        output_limits: Tuple[float, float],
        start_delay: float = 0,
    ):
        self.control_result = control_result
        self.feedback_result = feedback_result
        self.pid = PID(*gains, setpoint, output_limits=output_limits)
        self.start_time = datetime.now()
        self.start_delay = timedelta(seconds=start_delay)
        self.feedback_value = self.feedback_result.value
        self.last_feedback_value = self.feedback_value
        self.count_of_suspicious_readings = 0

    def update(self):
        """Update the PID controller."""

        time_elapsed = datetime.now() - self.start_time
        if time_elapsed > self.start_delay:
            self.last_feedback_value = self.feedback_value
            self.feedback_value = self.feedback_result.value
            feedback_value_change = abs(self.feedback_value - self.last_feedback_value)
            if feedback_value_change > 10 or self.feedback_value < 0:
                self.control_result.write(0)
                raise Exception(
                    "The PID feedback sensor value seems incorrect. Aborting."
                )
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

    def __init__(
        self,
        path: str,
        results: List[Result],
    ):
        self.paths: List[str] = []
        self.result_groups: List[List[Result]] = []
        self.fieldname_groups: List[List[str]] = []
        self.time = datetime.now()
        self.add(path, results)

    def add(self, path: str, results: List[Result]):
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

        (path, ext) = splitext(path)

        # The ":" in ISO time strings is not supported by filenames
        file_time = self.time.isoformat(timespec="seconds").replace(":", "-")

        path = f"{path}_{file_time}{ext}"

        # Compose the fieldnames and first row of values
        sources = [f"{result.source.name} ({result.source.unit})" for result in results]
        fieldnames = ["time"] + sources
        values = [self.time.isoformat()] + [result.value for result in results]
        to_write = dict(zip(fieldnames, values))

        # Create the CSV, writing the header and the first row of values
        with open(path, "w", newline="") as csv_file:
            csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerow(to_write)

        # Record the file and results for writing additional rows later.
        self.paths.append(path)
        self.result_groups.append(results)
        self.fieldname_groups.append(fieldnames)

    def update(self):
        """Update results and write the new data to CSV."""

        if DEBUG:
            sleep(DELAY_DEBUG)
        else:
            sleep(DELAY)
        self.time = datetime.now().isoformat()
        for results in self.result_groups:
            for result in results:
                result.update()
        self.write()

    def write(self):
        """Write data to CSV."""

        for path, results, fieldnames in zip(
            self.paths, self.result_groups, self.fieldname_groups
        ):
            values = [self.time] + [result.value for result in results]
            to_write = dict(zip(fieldnames, values))

            with open(path, "a", newline="") as csv_file:
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

    Attributes
    ----------
    all_results: List[Result]
    all_curves: List[pyqtgraph.PlotCurveItem]
    all_histories: List[Deque]
    time: List[int]
    """

    window = pyqtgraph.GraphicsLayoutWidget()

    def __init__(
        self,
        title: str,
        results: List[Result],
        row: int = 0,
        col: int = 0,
    ):
        self.all_results: List[Result] = []
        self.all_curves: List[pyqtgraph.PlotCurveItem] = []
        self.all_histories: List[Deque] = []
        self.time: List[int] = [-i * DELAY for i in range(0, HISTORY_LENGTH)]
        self.time.reverse()
        self.add(title, results, row, col)

    def add(self, title: str, results: List[Result], row: int, col: int):
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
        for i, (history, name) in enumerate(zip(histories, names)):
            curve = plot.plot(self.time, history, pen=pyqtgraph.intColor(i), name=name)
            self.all_curves.append(curve)

    def update(self):
        """Update plots."""
        for curve, history in zip(self.all_curves, self.all_histories):
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
        self, writer: Writer, plotter: Plotter, controller: Optional[Controller] = None
    ):
        self.writer = writer
        self.plotter = plotter
        self.controller = None if controller is None else controller
        self.plot_window_open = False

    def write_loop(self):
        """The CSV writer function to be looped in the write/control thread."""

        while self.plot_window_open:
            self.writer.update()

    def plot_loop(self):
        """The function to be looped in the plot thread."""

        self.plotter.update()

    def write_control_loop(self):
        """The control function to be looped in the write/control thread."""

        while self.plot_window_open:
            self.writer.update()
            self.controller.update()

    def start(self):
        """Start the write/control thread and plot on the main thread."""

        self.plot_window_open = True
        if self.controller is None:
            write_thread = Thread(target=self.write_loop)
        else:
            write_thread = Thread(target=self.write_control_loop)
        write_thread.start()
        plot_timer = pyqtgraph.QtCore.QTimer()
        plot_timer.timeout.connect(self.plot_loop)
        plot_timer.start()
        self.plotter.window.show()
        pyqtgraph.mkQApp().exec_()
        self.plot_window_open = False
