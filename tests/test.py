from __future__ import annotations

from time import localtime, sleep, strftime
from typing import List, NamedTuple

import boilerdaq as bd

sensors_path = "config/sensors.csv"
flux_params_path = "config/flux_params.csv"
raw_results_path = "results/raw_results.csv"
results_path = "results/results.csv"
delay = 0.25


# get all readings
all_sensors = bd.Sensor.get(sensors_path)
time = strftime("%Y-%m-%d %H:%M:%S", localtime())
all_readings = []
all_scaled_readings = []
for sensor in all_sensors:
    reading = bd.Reading(sensor)
    all_readings.append(reading)
    all_scaled_readings.append(bd.ScaledReading(reading))

# get flux parameters
flux_params = bd.FluxParam.get(flux_params_path, all_sensors)
# get fluxes
all_fluxes = []
for flux_param in flux_params:
    all_fluxes.append(bd.Flux(flux_param, all_scaled_readings))

# start writing
writer = bd.Writer(raw_results_path, time, all_readings)
writer.create(results_path, time, all_scaled_readings + all_fluxes)
for i in range(1000):
    writer.update()


# build list of sensor groups, grouped by name
sensor_groups = [bd.SensorGroup("all", all_sensors)]
raw_reading_groups = []
scaled_reading_groups = []
groups_dict = {
    "base": [0],
    "post": [1, 2, 3, 4],
    "top": [5],
    "water": [6, 7, 8],
    "pressure": [9],
}
for name, idx in groups_dict.items():
    sensors = [all_sensors[i] for i in idx]
    sensor_group = bd.SensorGroup(name, sensors)
    sensor_groups.append(sensor_group)

    raw_reading_group = bd.ResultGroup.get(sensor_group, all_readings)
    raw_reading_groups.append(raw_reading_group)

    scaled_reading_group = bd.ResultGroup.get(
        sensor_group, all_scaled_readings
    )
    scaled_reading_groups.append(scaled_reading_group)

...
# [r.update() for r in all_readings]
# [f.update() for f in all_fluxes]


# results_raw_path, raw_fieldnames = bd.csv_create_results(
#     results_raw_path, time, all_readings
# )

# plot = bd.Plot(readings)

# readings = bd.calibrate_readings(readings)
# all_fluxes = bd.get_fluxes(readings, flux_params)
# results_cal_path, cal_fieldnames = bd.csv_create_results(
#     results_cal_path, time_read, readings + all_fluxes
# )

# # daq loop start in background
# daq_thread = bd.Thread(
#     target=daq_loop,
#     args=(
#         plot.do_plot,
#         sensors,
#         delay,
#         results_raw_path,
#         raw_fieldnames,
#         flux_params,
#         results_cal_path,
#         cal_fieldnames,
#         plot.caches,
#     ),
# )
# daq_thread.daemon = True
# daq_thread.start()

# plot.start()
