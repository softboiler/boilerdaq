from __future__ import annotations

from time import localtime, sleep, strftime
from typing import List, NamedTuple, OrderedDict

import pyqtgraph

import boilerdaq as bd

sensors_path = "config/run/0_sensors.csv"
scaled_params_path = "config/run/1_scaled_params.csv"
flux_params_path = "config/run/2_flux_params.csv"
extrap_params_path = "config/run/3_extrap_params.csv"
readings_path = "results/readings.csv"
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

# get flux parameters
flux_params = bd.FluxParam.get(flux_params_path)
# get fluxes
fluxes = []
for param in flux_params:
    result = bd.Flux(param, scaled_results)
    fluxes.append(result)

# get extrapolation parameters
extrap_params = bd.ExtrapParam.get(extrap_params_path)
# get extrapolated results
extrap_results = []
for param in extrap_params:
    result = bd.ExtrapResult(param, scaled_results + fluxes)
    extrap_results.append(result)

# combine calculated results into one list
results = scaled_results + fluxes + extrap_results

# start writing
writer = bd.Writer(readings_path, time, readings)
writer.add(results_path, time, results)

# build list of sensor groups, grouped by name
group_dict = OrderedDict(
    [
        ("base", "T0cal"),
        ("post", "T1cal T2cal T3cal T4cal"),
        ("top", "T5cal T6ext"),
        ("water", "Tw1cal Tw2cal Tw3cal"),
        ("pressure", "Pcal"),
        ("flux", "Q12 Q23 Q34"),
    ]
)
group = bd.ResultGroup(group_dict, results)

# add groups of curves to different plot regions
plotter = bd.Plotter("base", group["base"], 0, 0)
plotter.add("post", group["post"], 0, 1)
plotter.add("top", group["top"], 0, 2)
plotter.add("water", group["water"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)
plotter.add("flux", group["flux"], 1, 2)

# start the write and plot loops
looper = bd.Looper(writer, plotter)
looper.start()
