from collections import deque, namedtuple
from csv import DictReader, DictWriter
from os.path import isfile, splitext
from threading import Thread
from time import localtime, sleep, strftime
from random import random

import pyqtgraph
from mcculw.ul import ULError, t_in, t_in_scan, v_in


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
        if sensor.type == "temperature":
            try:
                unit_int = unit_types[sensor.raw_unit]
                reading = t_in(sensor.board, sensor.channel, unit_int)
            except ULError:
                # reading = float("nan")
                reading = random()
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
                reading.value * reading.source.scale
                + reading.source.offset,
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
