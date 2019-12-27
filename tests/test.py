from __future__ import annotations

from time import localtime, sleep, strftime
from typing import List, NamedTuple, OrderedDict

import boilerdaq as bd

sensors_path = "config/sensors.csv"
flux_params_path = "config/flux_params.csv"
extrap_params_path = "config/extrap_params.csv"
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
    all_scaled_readings.append(bd.ScaledResult(reading))

# get flux parameters
flux_params = bd.FluxParam.get(flux_params_path, all_sensors)
# get fluxes
all_fluxes = []
for flux_param in flux_params:
    all_fluxes.append(bd.Flux(flux_param, all_scaled_readings))

# get extrapolation parameters
extrap_params = bd.ExtrapParam.get(extrap_params_path)

# start writing
writer = bd.Writer(raw_results_path, time, all_readings)
writer.add(results_path, time, all_scaled_readings + all_fluxes)
for _ in range(10):
    writer.update()


# build list of sensor groups, grouped by name
group_dict = OrderedDict(
    [
        ("base", "T0"),
        ("post", "T1 T2 T3 T4"),
        # ("top", "T5 T6"),
        ("top", "T5"),
        ("water", "Tw1 Tw2 Tw3"),
        ("pressure", "P"),
        ("flux", "Q12 Q23 Q34"),
    ]
)

group = bd.ResultGroup(group_dict, all_scaled_readings + all_fluxes)
for key, val in group.items():
    print(key)
    print([r.source.name for r in val])

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
