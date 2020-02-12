from __future__ import annotations

from collections import OrderedDict, deque
from csv import DictReader, DictWriter
from os.path import splitext
from statistics import mean
from threading import Thread
from time import localtime, sleep, strftime
from typing import Deque, List, NamedTuple

import pyqtgraph
from mcculw.ul import ULError, t_in, v_in
from numpy import exp, log, random
from scipy.optimize import curve_fit

pyqtgraph.setConfigOptions(antialias=True)
START_TIME = strftime("%Y-%m-%d %H:%M:%S", localtime())
DELAY = 2  # read/write/plot timestep
HISTORY_LENGTH = 300  # points to keep for plotting
SUBHIST_LENGTH = int(0.1 * HISTORY_LENGTH)  # history for running avg
DEBUG = False  # run with simulated DAQs when real DAQs unavailable
RISE_DESIRED = 0.85
NUM_TAUS = -log(1 - RISE_DESIRED)
if DEBUG:
    DELAY_DEBUG = 0.05  # actual timestep, still use DELAY in plot
    # parameters for simulated noisy 1st-order system signal
    GAIN_DEBUG = 100
    TAU_DEBUG = DELAY * HISTORY_LENGTH
    NOISE_SCALE = 1e-2


class Sensor(NamedTuple):
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
        self.tau_guess = DELAY / 3
        self.rise = float("nan")
        self.timeleft = float("nan")

    def update(self):
        self.history.append(self.value)
        self.subhist_new.append(self.value)
        if self.source.est_rise:
            if len(self.subhist_ini) < SUBHIST_LENGTH:
                self.subhist_ini.append(self.value)
                self.avg_ini = mean(self.subhist_ini)
            elif self.time[0] > 0:
                self.avg_new = mean(self.subhist_new)
                try:
                    fit = curve_fit(
                        lambda time, gain, tau: gain * (1 - exp(-time / tau)),
                        list(self.time),
                        list(self.history) - self.avg_ini,
                        p0=(self.gain_guess, self.tau_guess),
                    )
                    gain_fit = fit[0][0]
                    self.rise = self.gain_guess / gain_fit
                    tau_fit = fit[0][1]
                    self.timeleft = (NUM_TAUS * tau_fit - self.time[-1]) / 60
                except RuntimeError:
                    self.rise = float("nan")
                    self.timeleft = float("nan")
                self.gain_guess = self.avg_new - self.avg_ini
                self.tau_guess = (self.time[-1]) / 3
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
                self.value = t_in(
                    self.source.board, self.source.channel, unit_int
                )
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
        self.value = (
            self.unscaled_result.value * self.source.scale + self.source.offset
        )
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
            self.flux_result.value
            * self.source.length
            / self.source.conductivity
        )
        super().update()


class ResultGroup(OrderedDict):
    def __init__(self, group_dict: OrderedDict, results: List[Result]):
        for key, val in group_dict.items():
            result_names = val.split()
            filtered_results = []
            for name in result_names:
                result = Result.get(name, results)
                filtered_results.append(result)
            self[key] = filtered_results


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
        file_time = START_TIME.replace(" ", "_").replace(":", "-")
        path = path + "_" + file_time + ext

        sources = [r.source.name + " (" + r.source.unit + ")" for r in results]
        fieldnames = ["time"] + sources
        values = [START_TIME] + [r.value for r in results]
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
        self.update_time = strftime("%Y-%m-%d %H:%M:%S", localtime())
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
            curve = plot.plot(
                self.time, history, pen=pyqtgraph.intColor(i), name=name
            )
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
                timeleft_str = "time left: " + str(timeleft)[0:4] + " min"
                label.setText(sig + " (" + rise_str + ", " + timeleft_str + ")")
            curve.setData(self.time, history)


class Looper:
    def __init__(self, writer: Writer, plotter: Plotter):
        self.writer = writer
        self.plotter = plotter

    def write_loop(self):
        while self.plot_window_open:
            self.writer.update()

    def plot_loop(self):
        self.plotter.update()

    def start(self):
        self.plot_window_open = True
        write_thread = Thread(target=self.write_loop)
        write_thread.start()
        plot_timer = pyqtgraph.QtCore.QTimer()
        plot_timer.timeout.connect(self.plot_loop)
        plot_timer.start()
        pyqtgraph.Qt.QtGui.QApplication.instance().exec_()
        self.plot_window_open = False
