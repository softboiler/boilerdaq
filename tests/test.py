from __future__ import annotations

from time import localtime, sleep, strftime
from typing import List, NamedTuple, OrderedDict

import boilerdaq as bd

sensors_path = "config/0_sensors.csv"
scaled_params_path = "config/1_scaled_params.csv"
flux_params_path = "config/2_flux_params.csv"
extrap_params_path = "config/3_extrap_params.csv"
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
for _ in range(10):
    writer.update()


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
