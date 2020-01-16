from __future__ import annotations

from time import localtime, sleep, strftime
from typing import List, NamedTuple, OrderedDict

import pyqtgraph

import boilerdaq as bd

sensors_path = "config/cal/0_sensors.csv"
scaled_params_path = "config/cal/1_scaled_params.csv"
results_path = "results/results.csv"

# get all readings
all_sensors = bd.Sensor.get(sensors_path)
time = strftime("%Y-%m-%d %H:%M:%S", localtime())
readings = []
for sensor in all_sensors:
    reading = bd.Reading(sensor)
    readings.append(reading)

# get scaled parameters
scaled_params = bd.ScaledParam.get(scaled_params_path)
# get scaled results
scaled_results = []
for param in scaled_params:
    result = bd.ScaledResult(param, readings)
    scaled_results.append(result)

# combine calculated results into one list
results = readings + scaled_results

# start writing
writer = bd.Writer(results_path, time, results)

# build list of sensor groups, grouped by name
group_dict = OrderedDict(
    [
        ("uncalibrated", "T0 T1 T2 T3 T4 T5 Tw1 Tw2 Tw3"),
        ("calibrated", "T0cal T1cal T2cal T3cal T4cal T5cal Tw1cal Tw2cal Tw3cal"),
        ("pressure_volts","P"),
        ("pressure", "Pcal"),
        ("debug", "Tdbg"),
    ]
)
group = bd.ResultGroup(group_dict, results)

# add groups of curves to different plot regions
plotter = bd.Plotter("uncalibrated", group["uncalibrated"], 0, 0)
plotter.add("calibrated", group["calibrated"], 0, 1)
plotter.add("pressure_volts", group["pressure_volts"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)
plotter.add("debug", group["debug"], 0, 2)


# start the write and plot loops
looper = bd.Looper(writer, plotter)
looper.start()
