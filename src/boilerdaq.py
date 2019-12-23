from collections import deque, namedtuple
from csv import DictReader, DictWriter
from os.path import isfile, splitext
from threading import Thread
from time import localtime, sleep, strftime
from random import random

import pyqtgraph
from mcculw.ul import ULError, t_in, t_in_scan, v_in

_debug = True
pyqtgraph.setConfigOptions(antialias=True)
Result = namedtuple("Result", ["source", "value"])


def csv_read_sensors(path):
    def get_sensor(row, fieldnames):
        Sensor = namedtuple("Sensor", fieldnames)
        sensor = Sensor(
            row["name"],
            int(row["board"]),
            int(row["channel"]),
            row["type"],
            row["raw_unit"],
            float(row["scale"]),
            float(row["offset"]),
            row["cal_unit"],
        )
        return sensor

    sensors = []
    with open(path) as csv_file:
        reader = DictReader(csv_file)
        fieldnames = reader.fieldnames
        for row in reader:
            sensor = get_sensor(row, fieldnames)
            sensors.append(sensor)

    return sensors


def csv_read_flux_params(flux_params_csv, sensors):
    def get_flux_param(row, fieldnames):
        FluxParam = namedtuple("FluxParam", fieldnames)
        flux_param = FluxParam(
            row["name"],
            row["sensor_at_origin"],
            row["sensor_at_length"],
            float(row["conductivity"]),
            float(row["length"]),
        )
        return flux_param

    flux_params = []
    with open(flux_params_csv) as csv_file:
        reader = DictReader(csv_file)
        fieldnames = reader.fieldnames
        for row in reader:
            flux_param = get_flux_param(row, fieldnames)
            flux_params.append(flux_param)
    return flux_params


def read_sensors(sensors, delay):
    sleep(delay)
    readings = []
    time_read = strftime("%Y-%m-%d %H:%M:%S", localtime())
    unit_types = {"C": 0, "F": 1, "K": 2, "V": 5}
    for sensor in sensors:
        if _debug:
            reading = random()
        elif sensor.type == "temperature":
            try:
                unit_int = unit_types[sensor.raw_unit]
                reading = t_in(sensor.board, sensor.channel, unit_int)
            except ULError:
                reading = float("nan")
        elif sensor.type == "voltage":
            reading = v_in(sensor.board, sensor.channel, 0)
        readings.append(Result(sensor, reading))
    return time_read, readings


def calibrate_readings(readings):
    calibrated = []
    for reading in readings:
        calibrated.append(
            Result(
                reading.source,
                reading.value * reading.source.scale + reading.source.offset,
            )
        )
    return calibrated


def get_fluxes(readings, flux_params):
    fluxes = []
    sensor_names = [reading.source.name for reading in readings]
    for p in flux_params:
        i = sensor_names.index(p.sensor_at_origin)
        val_origin = readings[i].value
        j = sensor_names.index(p.sensor_at_length)
        val_length = readings[j].value
        flux = p.conductivity / p.length * (val_length - val_origin)
        fluxes.append(Result(p, flux))
    return fluxes


def csv_create_results(results_path, time_read, results):
    (path, ext) = splitext(results_path)
    time_path = time_read.replace(" ", "_").replace(":", "-")
    results_path = path + "_" + time_path + ext

    fieldnames = ["time"] + [result.source.name for result in results]
    values = [time_read] + [result.value for result in results]
    to_write = dict(zip(fieldnames, values))

    with open(results_path, "w", newline="") as csv_file:
        csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerow(to_write)

    return results_path, fieldnames


def csv_write_results(results_path, fieldnames, time_read, results):
    values = [time_read] + [result.value for result in results]
    to_write = dict(zip(fieldnames, values))
    with open(results_path, "a", newline="") as csv_file:
        csv_writer = DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writerow(to_write)


def daq_loop(
    do_plot,
    sensors,
    delay,
    results_raw_path,
    raw_fieldnames,
    flux_params,
    results_cal_path,
    cal_fieldnames,
    caches,
):
    while do_plot:
        time_read, readings = read_sensors(sensors, delay)
        csv_write_results(results_raw_path, raw_fieldnames, time_read, readings)

        # readings = calibrate_readings(readings)
        # fluxes = get_fluxes(readings, flux_params)
        # csv_write_results(
        #     results_cal_path, cal_fieldnames, time_read, readings + fluxes,
        # )

        for cache, reading in zip(caches, readings):
            cache.append(reading.value)


class Plot:
    def __init__(self, readings, window=pyqtgraph.GraphicsWindow(), cache_length=100):
        self.do_plot = True
        self.window = window

        self.caches = []
        for reading in readings:
            self.caches.append(deque([reading.value], maxlen=cache_length))

        self.plot = self.window.addPlot()

        self.curves = []
        for cache in self.caches:
            self.curves.append(self.plot.plot(cache))

    def start(self):
        timer = pyqtgraph.QtCore.QTimer()
        timer.timeout.connect(self.update_plot)
        timer.start()

        pyqtgraph.Qt.QtGui.QApplication.instance().exec_()
        self.do_plot = False

    def update_plot(self):
        for curve, cache in zip(self.curves, self.caches):
            curve.setData(cache)


def main():

    sensors_path = "config/sensors.csv"
    flux_params_path = "config/flux_params.csv"
    results_raw_path = "results/results_raw.csv"
    results_cal_path = "results/results_cal.csv"
    delay = 0.25

    # loop setup
    sensors = csv_read_sensors(sensors_path)
    flux_params = csv_read_flux_params(flux_params_path, sensors)

    time_read, readings = read_sensors(sensors, delay)
    results_raw_path, raw_fieldnames = csv_create_results(
        results_raw_path, time_read, readings
    )

    plot = Plot(readings)

    readings = calibrate_readings(readings)
    fluxes = get_fluxes(readings, flux_params)
    results_cal_path, cal_fieldnames = csv_create_results(
        results_cal_path, time_read, readings + fluxes
    )

    # daq loop start in background
    daq_thread = Thread(
        target=daq_loop,
        args=(
            plot.do_plot,
            sensors,
            delay,
            results_raw_path,
            raw_fieldnames,
            flux_params,
            results_cal_path,
            cal_fieldnames,
            plot.caches,
        ),
    )
    daq_thread.daemon = True
    daq_thread.start()

    plot.start()


if __name__ == "__main__":
    main()
