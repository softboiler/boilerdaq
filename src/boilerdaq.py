from __future__ import annotations

from collections import OrderedDict, deque
from csv import DictReader, DictWriter
from os.path import isfile, splitext
from random import random
from threading import Thread
from time import localtime, sleep, strftime
from typing import Dict, List, NamedTuple

import pyqtgraph
from mcculw.ul import ULError, t_in, t_in_scan, v_in

pyqtgraph.setConfigOptions(antialias=True)
DEBUG = False
if DEBUG:
    DELAY = 0.2
    HISTORY_LENGTH = 100
else:
    DELAY = 2
    HISTORY_LENGTH = 300

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
    def __init__(self, history_length: int = HISTORY_LENGTH):
        self.history = deque([], maxlen=history_length)
        for _ in range(history_length):
            self.history.append(0)
        self.value = None

    def update(self):
        self.history.append(self.value)

    @staticmethod
    def get(name: str, results: List[Result]) -> Result:
        result_names = [result.source.name for result in results]
        i = result_names.index(name)
        result = results[i]
        return result


# Reading: child of Result
class Reading(Result):
    unit_types = {"C": 0, "F": 1, "K": 2, "V": 5}

    def __init__(
        self, sensor: Sensor, history_length: int = HISTORY_LENGTH
    ):
        super().__init__(history_length)
        self.source = sensor
        self.update()

    def update(self):
        if DEBUG:
            self.value = random()
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
        super().__init__(history_length)
        self.source = scaled_param
        self.unscaled_result = Result.get(
            scaled_param.unscaled_sensor, results
        )
        self.update()

    def update(self):
        self.value = (
            self.unscaled_result.value * self.source.scale
            + self.source.offset
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
        super().__init__(history_length)
        self.source = flux_param
        self.origin_result = Result.get(
            flux_param.origin_sensor, results
        )
        self.distant_result = Result.get(
            flux_param.distant_sensor, results
        )
        self.update()

    def update(self):
        self.value = (
            self.source.conductivity
            / self.source.length
            * (self.distant_result.value - self.origin_result.value)
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
        super().__init__(history_length)
        self.source = extrap_param
        self.origin_result = Result.get(
            extrap_param.origin_sensor, results
        )
        self.flux_result = Result.get(extrap_param.flux, results)

        self.update()

    def update(self):
        self.value = (
            self.origin_result.value
            * self.flux_result.value
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
        self, path: str, start_time: str, results: List[Result],
    ):
        self.paths = []
        self.result_groups = []
        self.fieldname_groups = []
        self.add(path, start_time, results)

    def add(self, path, start_time, results):
        (path, ext) = splitext(path)
        file_time = start_time.replace(" ", "_").replace(":", "-")
        path = path + "_" + file_time + ext

        sources = [
            r.source.name + " (" + r.source.unit + ")" for r in results
        ]
        fieldnames = ["time"] + sources
        values = [start_time] + [r.value for r in results]
        to_write = dict(zip(fieldnames, values))

        with open(path, "w", newline="") as csv_file:
            csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerow(to_write)

        self.paths.append(path)
        self.result_groups.append(results)
        self.fieldname_groups.append(fieldnames)

    def update(self):
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
        self,
        title: str,
        results: List[Result],
        row: int = 0,
        col: int = 0,
    ):
        self.all_results = []
        self.all_curves = []
        self.time = []
        for i in range(0,HISTORY_LENGTH):
            self.time.append(-i*DELAY)
        self.time.reverse()
        self.add(title, results, row, col)

    def add(
        self, title: str, results: List[Result], row: int, col: int
    ):
        i = 0
        plot = self.window.addPlot(row, col)
        plot.addLegend()
        plot.setLabel("left", units=results[0].source.unit)
        plot.setLabel("bottom", units="s")
        plot.setTitle(title)
        histories = [r.history for r in results]
        names = [r.source.name for r in results]
        for history, name in zip(histories, names):
            self.all_curves.append(
                plot.plot(
                    self.time, history, pen=pyqtgraph.intColor(i), name=name
                )
            )
            i += 1
        self.all_results.extend(results)

    def update(self):
        all_histories = [r.history for r in self.all_results]
        for curve, history in zip(self.all_curves, all_histories):
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
