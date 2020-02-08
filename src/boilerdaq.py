from __future__ import annotations

from collections import OrderedDict, deque
from csv import DictReader, DictWriter
from os.path import isfile, splitext
from random import random
from statistics import mean
from threading import Thread
from time import localtime, sleep, strftime
from typing import Dict, List, NamedTuple

import pyqtgraph
from mcculw.ul import ULError, t_in, t_in_scan, v_in

pyqtgraph.setConfigOptions(antialias=True)
START_TIME = strftime("%Y-%m-%d %H:%M:%S", localtime())
DEBUG = False
if DEBUG:
    DELAY = 2
    HISTORY_LENGTH = 300
    GAIN_DEBUG = 100
    TAU_DEBUG = DELAY * HISTORY_LENGTH * 5
else:
    DELAY = 2
    HISTORY_LENGTH = 300
SUBHIST_LENGTH = int(0.1 * HISTORY_LENGTH)

# Sensor: used to obtain initial readings
class Sensor(NamedTuple):
    name: str
    board: int
    channel: int
    reading: str
    unit: str

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
                    )
                )
        return sensors


# Result: parent of Reading, ScaledResult, Flux, and ExtrapResult
class Result:
    def __init__(self):
        self.history = deque([], maxlen=HISTORY_LENGTH)
        for _ in range(HISTORY_LENGTH):
            self.history.append(0)
        self._subhist_new = deque([], maxlen=SUBHIST_LENGTH)
        self._subhist_old = deque([], maxlen=SUBHIST_LENGTH)
        for _ in range(SUBHIST_LENGTH):
            self._subhist_new.append(0)
            self._subhist_old.append(0)
        self.value = None

    def update(self):
        self.history.append(self.value)
        self._subhist_old.append(self.history[0])
        self._subhist_new.append(self.value)
        self.avg_old = mean(self._subhist_old)
        self.avg_new = mean(self._subhist_new)

    @staticmethod
    def get(name: str, results: List[Result]) -> Result:
        result_names = [result.source.name for result in results]
        i = result_names.index(name)
        result = results[i]
        return result


# Reading: child of Result
class Reading(Result):
    unit_types = {"C": 0, "F": 1, "K": 2, "V": 5}

    def __init__(self, sensor: Sensor, history_length: int = HISTORY_LENGTH):
        super().__init__()
        self.source = sensor
        self.update()

    def update(self):
        if DEBUG:
            self.value = GAIN_DEBUG * (
                1 - exp(-self.time[-1] / TAU_DEBUG)
            ) + random.normal(scale=1e-2 * GAIN_DEBUG)
        elif self.source.reading == "temperature":
            try:
                unit_int = self.unit_types[self.source.unit]
                self.value = t_in(
                    self.source.board, self.source.channel, unit_int
                )
            except ULError:
                self.value = float("nan")
        elif self.source.reading == "voltage":
            self.value = v_in(self.source.board, self.source.channel, 0)
        super().update()


# ScaledResult: child of Result, built by ScaledParam
class ScaledParam(NamedTuple):
    name: str
    unscaled_sensor: str
    scale: float
    offset: float
    unit: str

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
                    )
                )
        return params


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


# Flux: child of Result, built by FluxParam
class FluxParam(NamedTuple):
    name: str
    origin_sensor: str
    distant_sensor: str
    conductivity: float
    length: float
    unit: str

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
                    )
                )
        return params


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


# ExtrapResult: child of Result, built by ExtrapParam
class ExtrapParam(NamedTuple):
    name: str
    origin_sensor: str
    flux: str
    conductivity: float
    length: float
    unit: str

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
                    )
                )
        return params


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


# grouping, writing, and plotting
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
        self.paths = []
        self.result_groups = []
        self.fieldname_groups = []
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
        if not DEBUG:
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
        self.all_plots = []
        self.all_results = []
        self.all_curves = []
        self.all_labels = []
        self.all_sigs = []
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
        histories = [r.history for r in results]
        names = [r.source.name for r in results]
        avg_olds = [r.avg_old for r in results]
        avg_news = [r.avg_new for r in results]
        for history, name, avg_old, avg_new in zip(
            histories, names, avg_olds, avg_news
        ):
            curve = plot.plot(
                self.time, history, pen=pyqtgraph.intColor(i), name=name
            )
            self.all_curves.append(curve)

            label = legend.items[-1][-1]
            sig = label.text
            diff = " (diff: " + str(avg_new - avg_old)[0:7] + ")"
            label.setText(sig + diff)
            self.all_labels.append(label)
            self.all_sigs.append(sig)
            i += 1
        self.all_plots.append(plot)
        self.all_results.extend(results)

    def update(self):
        avg_olds = [r.avg_old for r in self.all_results]
        avg_news = [r.avg_new for r in self.all_results]
        all_histories = [r.history for r in self.all_results]
        for label, sig, curve, avg_old, avg_new, history in zip(
            self.all_labels,
            self.all_sigs,
            self.all_curves,
            avg_olds,
            avg_news,
            all_histories,
        ):
            diff = " (diff: " + str(avg_new - avg_old)[0:7] + ")"
            label.setText(sig + diff)
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
