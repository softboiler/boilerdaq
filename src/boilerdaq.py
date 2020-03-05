from __future__ import annotations

from collections import OrderedDict, deque
from csv import DictReader, DictWriter
from datetime import datetime
from os.path import splitext
from statistics import mean
from threading import Thread
from time import sleep
from typing import Deque, List, NamedTuple, Tuple

import pyqtgraph
from mcculw.ul import ULError, t_in, v_in
from numpy import exp, log, random
from scipy.optimize import curve_fit
from simple_pid import PID

pyqtgraph.setConfigOptions(antialias=True)
DELAY = 2  # read/write/plot timestep
HISTORY_LENGTH = 300  # points to keep for plotting and fitting
SUBHIST_RATIO = 0.2  # portion of history length to base initial averages off of
RISE_DESIRED = 0.90  # desired rise as a fraction of total estimated rise
DEBUG = False  # if True, run with simulated DAQs

SUBHIST_LENGTH = int(SUBHIST_RATIO * HISTORY_LENGTH)  # history for running avg
NUM_TAUS = -log(1 - RISE_DESIRED)  # to estimate time until desired rise

if DEBUG:
    DELAY_DEBUG = 0.2
    GAIN_DEBUG = 100
    TAU_DEBUG = DELAY * HISTORY_LENGTH
    NOISE_SCALE = 1e-2


class Sensor(NamedTuple):
    """
    Information about a sensor.

    A subclass of `NamedTuple`,

    Attributes:
    - `name (str)`: Name of the sensor.
    - `board (int)`: Which board the sensor belongs to.
    - `channel (int)`: The channel pointing to this sensor on the board.
    - `reading (int)`: The sensor type, either "Temperature" or "Voltage"
    - `unit (str)`: The unit type for values reported by the board.

    Methods:
    - `get(cls, path: str) -> List[Sensor]`
        - Processes a CSV file at `path`, returning a `List` of `Sensor`.

    """

    name: str
    board: int
    channel: int
    reading: str
    unit: str
    est_rise: bool

    @classmethod
    def get(cls, path: str) -> List[Sensor]:
        sensors = []
        with open(path) as csv_file:
            reader = DictReader(csv_file)
            for row in reader:
                sensors.append(
                    cls(
                        row["name"],
                        int(row["board"]),
                        int(row["channel"]),
                        row["reading"],
                        row["unit"],
                        bool(int(row["est_rise"])),
                    )
                )
        return sensors


class ScaledParam(NamedTuple):
    name: str
    unscaled_sensor: str
    scale: float
    offset: float
    unit: str
    est_rise: bool

    @classmethod
    def get(cls, path: str) -> List[ScaledParam]:
        params = []
        with open(path) as csv_file:
            reader = DictReader(csv_file)
            for row in reader:
                params.append(
                    cls(
                        row["name"],
                        row["unscaled_sensor"],
                        float(row["scale"]),
                        float(row["offset"]),
                        str(row["unit"]),
                        bool(int(row["est_rise"])),
                    )
                )
        return params


class FluxParam(NamedTuple):
    name: str
    origin_sensor: str
    distant_sensor: str
    conductivity: float
    length: float
    unit: str
    est_rise: bool

    @classmethod
    def get(cls, path: str) -> List[FluxParam]:
        params = []
        with open(path) as csv_file:
            reader = DictReader(csv_file)
            for row in reader:
                params.append(
                    cls(
                        row["name"],
                        row["origin_sensor"],
                        row["distant_sensor"],
                        float(row["conductivity"]),
                        float(row["length"]),
                        row["unit"],
                        bool(int(row["est_rise"])),
                    )
                )
        return params


class ExtrapParam(NamedTuple):
    name: str
    origin_sensor: str
    flux: str
    conductivity: float
    length: float
    unit: str
    est_rise: bool

    @classmethod
    def get(cls, path: str) -> List[ExtrapParam]:
        params = []
        with open(path) as csv_file:
            reader = DictReader(csv_file)
            for row in reader:
                params.append(
                    cls(
                        row["name"],
                        row["origin_sensor"],
                        row["flux"],
                        float(row["conductivity"]),
                        float(row["length"]),
                        row["unit"],
                        bool(int(row["est_rise"])),
                    )
                )
        return params


class PowerParam(NamedTuple):
    name: str
    unit: str

    @classmethod
    def get(cls, path: str) -> List[PowerParam]:
        power_supplies = []
        with open(path) as csv_file:
            reader = DictReader(csv_file)
            for row in reader:
                power_supplies.append(cls(row["name"], row["unit"],))
        return power_supplies


class Result:
    def __init__(self):
        self.source = None
        self.value = None
        self.time = deque([], maxlen=HISTORY_LENGTH)
        self.history = deque([], maxlen=HISTORY_LENGTH)
        self.subhist_new = deque([], maxlen=SUBHIST_LENGTH)
        self.subhist_ini = []
        for _ in range(HISTORY_LENGTH):
            self.time.append(0)
            self.history.append(0)
            self.subhist_new.append(0)
        self.gain_guess = 0
        self.tau_guess = DELAY
        self.rise = float("nan")
        self.timeleft = float("nan")

    @staticmethod
    def function_to_fit(time, gain, tau):
        return gain * (1 - exp(-time / tau))

    def update(self):
        self.history.append(self.value)
        self.subhist_new.append(self.value)
        if self.source.est_rise:
            if len(self.subhist_ini) < SUBHIST_LENGTH:
                self.subhist_ini.append(self.value)
                self.avg_ini = mean(self.subhist_ini)
            elif self.time[0] > 0:
                time = list(self.time)
                values = [value - self.avg_ini for value in self.history]
                guess = (self.gain_guess, self.tau_guess)
                gain_bounds = sorted([0, 100 * self.gain_guess])
                if gain_bounds[0] == gain_bounds[1]:
                    gain_bounds[1] = gain_bounds[0] + 1
                tau_bounds = sorted([0, 100 * self.tau_guess])
                if tau_bounds[0] == tau_bounds[1]:
                    tau_bounds[1] = tau_bounds[0] + 1
                bounds = (
                    [gain_bounds[0], tau_bounds[0]],
                    [gain_bounds[1], tau_bounds[1]],
                )
                try:
                    fit = curve_fit(
                        self.function_to_fit, time, values, p0=guess, bounds=bounds,
                    )
                    gain_fit = fit[0][0]
                    self.rise = self.gain_guess / gain_fit
                    tau_fit = fit[0][1]
                    self.timeleft = (NUM_TAUS * tau_fit - self.time[-1]) / 60
                except RuntimeError:
                    self.rise = float("nan")
                    self.timeleft = float("nan")
                self.avg_new = mean(self.subhist_new)
                self.gain_guess = self.avg_new - self.avg_ini
                self.tau_guess = self.time[-1]
        self.time.append(self.time[-1] + DELAY)

    @staticmethod
    def get(name: str, results: List[Result]) -> Result:
        result_names = [result.source.name for result in results]
        i = result_names.index(name)
        result = results[i]
        return result


class Reading(Result):
    unit_types = {"C": 0, "F": 1, "K": 2, "V": 5}

    def __init__(self, sensor: Sensor, history_length: int = HISTORY_LENGTH):
        super().__init__()
        if DEBUG:
            self.debug_offset = random.normal(scale=GAIN_DEBUG)
        self.source = sensor
        self.update()

    def update(self):
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
    def __init__(
        self,
        scaled_param: ScaledParam,
        results: List[Result],
        history_length: int = HISTORY_LENGTH,
    ):
        super().__init__()
        self.source = scaled_param
        self.unscaled_result = Result.get(scaled_param.unscaled_sensor, results)
        self.update()

    def update(self):
        self.value = self.unscaled_result.value * self.source.scale + self.source.offset
        super().update()


class Flux(Result):
    def __init__(
        self,
        flux_param: FluxParam,
        results: List[Result],
        history_length: int = HISTORY_LENGTH,
    ):
        super().__init__()
        self.source = flux_param
        self.origin_result = Result.get(flux_param.origin_sensor, results)
        self.distant_result = Result.get(flux_param.distant_sensor, results)
        self.update()

    def update(self):
        self.value = (
            self.source.conductivity
            / self.source.length
            * (self.origin_result.value - self.distant_result.value)
        )
        super().update()


class ExtrapResult(Result):
    def __init__(
        self,
        extrap_param: ExtrapParam,
        results: List[Result],
        history_length: int = HISTORY_LENGTH,
    ):
        super().__init__()
        self.source = extrap_param
        self.origin_result = Result.get(extrap_param.origin_sensor, results)
        self.flux_result = Result.get(extrap_param.flux, results)

        self.update()

    def update(self):
        self.value = self.origin_result.value - (
            self.flux_result.value * self.source.length / self.source.conductivity
        )
        super().update()


class PowerResult(Result):
    def __init__(
        self, power_param: PowerParam, instrument, history_length: int = HISTORY_LENGTH,
    ):
        self.source = power_param
        self.instrument = instrument
        self.update()

    def update(self):
        if self.source.name == "V":
            self.value = float(self.instrument.query("measure:voltage?"))
        elif self.source.name == "I":
            self.value = float(self.instrument.query("measure:current?"))
        pass

    def write(self, value):
        if self.source.name == "V":
            self.instrument.write("source:voltage " + str(value))
        elif self.source.name == "I":
            self.instrument.write("source:current " + str(value))


class ResultGroup(OrderedDict):
    def __init__(self, group_dict: OrderedDict, results: List[Result]):
        for key, val in group_dict.items():
            result_names = val.split()
            filtered_results = []
            for name in result_names:
                result = Result.get(name, results)
                filtered_results.append(result)
            self[key] = filtered_results


class Controller:
    def __init__(
        self,
        control_result: PowerResult,
        feedback_result: Result,
        setpoint: float,
        gains: List[float],
        output_limits: Tuple[float, float],
    ):
        self.control_result = control_result
        self.feedback_result = feedback_result
        self.pid = PID(
            gains[0], gains[1], gains[2], setpoint, output_limits=output_limits
        )

    def update(self):
        feedback_value = self.feedback_result.value
        control_value = self.pid(feedback_value)
        print(f"{feedback_value} {control_value}")
        self.control_result.write(control_value)


class Writer:
    def __init__(
        self, path: str, results: List[Result],
    ):
        self.paths: List[str] = []
        self.result_groups: List[List[Result]] = []
        self.fieldname_groups: List[str] = []
        self.add(path, results)

    def add(self, path, results):
        (path, ext) = splitext(path)
        start_time = datetime.now()
        file_time = start_time.isoformat(timespec="seconds").replace(":", "-")
        path = path + "_" + file_time + ext

        sources = [r.source.name + " (" + r.source.unit + ")" for r in results]
        fieldnames = ["time"] + sources
        values = [start_time.isoformat()] + [r.value for r in results]
        to_write = dict(zip(fieldnames, values))

        with open(path, "w", newline="") as csv_file:
            csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerow(to_write)

        self.paths.append(path)
        self.result_groups.append(results)
        self.fieldname_groups.append(fieldnames)

    def update(self):
        if DEBUG:
            sleep(DELAY_DEBUG)
        else:
            sleep(DELAY)
        self.update_time = datetime.now().isoformat()
        for results in self.result_groups:
            [r.update() for r in results]
        self.write()

    def write(self):
        for path, results, fieldnames in zip(
            self.paths, self.result_groups, self.fieldname_groups
        ):
            values = [self.update_time] + [r.value for r in results]
            to_write = dict(zip(fieldnames, values))

            with open(path, "a", newline="") as csv_file:
                csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
                csv_writer.writerow(to_write)


class Plotter:
    window = pyqtgraph.GraphicsWindow()

    def __init__(
        self, title: str, results: List[Result], row: int = 0, col: int = 0,
    ):
        self.all_results: List[Result] = []
        self.all_curves: List[pyqtgraph.PlotCurveItem] = []
        self.all_labels: List[pyqtgraph.LabelItem] = []
        self.all_sigs: List[str] = []
        self.all_histories: List[Deque] = []
        self.time = []
        for i in range(0, HISTORY_LENGTH):
            self.time.append(-i * DELAY)
        self.time.reverse()
        self.add(title, results, row, col)

    def add(self, title: str, results: List[Result], row: int, col: int):
        i = 0
        plot = self.window.addPlot(row, col)
        legend = plot.addLegend()
        plot.setLabel("left", units=results[0].source.unit)
        plot.setLabel("bottom", units="s")
        plot.setTitle(title)
        self.all_results.extend(results)
        histories = [r.history for r in results]
        self.all_histories.extend(histories)
        names = [r.source.name for r in results]
        for history, name in zip(histories, names):
            curve = plot.plot(self.time, history, pen=pyqtgraph.intColor(i), name=name)
            self.all_curves.append(curve)
            label = legend.items[-1][-1]
            self.all_labels.append(label)
            sig = label.text
            self.all_sigs.append(sig)
            i += 1

    def update(self):
        self.zipped = zip(
            self.all_curves,
            self.all_labels,
            self.all_sigs,
            self.all_histories,
            [r.rise for r in self.all_results],
            [r.timeleft for r in self.all_results],
            [r.source.est_rise for r in self.all_results],
        )
        for curve, label, sig, history, rise, timeleft, est_rise in self.zipped:
            if est_rise:
                rise_str = "rise: " + str(rise)[0:4]
                timeleft_str = (
                    "time until "
                    + str(RISE_DESIRED)[0:4]
                    + ": "
                    + str(timeleft)[0:4]
                    + " min"
                )
                label.setText(sig + " (" + rise_str + ", " + timeleft_str + ")")
            curve.setData(self.time, history)


class Looper:
    def __init__(self, writer: Writer, plotter: Plotter, controller: Controller = None):
        self.writer = writer
        self.plotter = plotter
        if controller is None:
            self.controller = None
        else:
            self.controller = controller

    def write_loop(self):
        while self.plot_window_open:
            self.writer.update()

    def plot_loop(self):
        self.plotter.update()

    def write_control_loop(self):
        while self.plot_window_open:
            self.writer.update()
            self.controller.update()

    def start(self):
        self.plot_window_open = True
        if self.controller is None:
            write_thread = Thread(target=self.write_loop)
            write_thread.start()
        else:
            write_thread = Thread(target=self.write_control_loop)
            write_thread.start()

        plot_timer = pyqtgraph.QtCore.QTimer()
        plot_timer.timeout.connect(self.plot_loop)
        plot_timer.start()
        pyqtgraph.Qt.QtGui.QApplication.instance().exec_()
        self.plot_window_open = False
