"""Run the data acquisition loop."""

from __future__ import annotations

import boilerdaq as bd

SENSORS_PATH = "config/1_sensors.csv"
SCALED_PARAMS_PATH = "config/2_scaled_params.csv"
FLUX_PARAMS_PATH = "config/3_flux_params.csv"
EXTRAP_PARAMS_PATH = "config/4_extrap_params.csv"
RESULTS_PATH = "results/results.csv"

BOILING_CURVE_PATH = "results/curve.csv"

# Get all readings
all_sensors = bd.Sensor.get(SENSORS_PATH)
readings = []
for sensor in all_sensors:
    reading = bd.Reading(sensor)
    readings.append(reading)

# Get scaled parameters
scaled_params = bd.ScaledParam.get(SCALED_PARAMS_PATH)
# Get scaled results
scaled_results = []
for param in scaled_params:
    result = bd.ScaledResult(param, readings)
    scaled_results.append(result)

# Get flux parameters
flux_params = bd.FluxParam.get(FLUX_PARAMS_PATH)
# Get fluxes
fluxes = []
for param in flux_params:
    result = bd.Flux(param, scaled_results)
    fluxes.append(result)

# Get extrapolation parameters
extrap_params = bd.ExtrapParam.get(EXTRAP_PARAMS_PATH)
# Get extrapolated results
extrap_results = []
for param in extrap_params:
    result = bd.ExtrapResult(param, scaled_results + fluxes)
    extrap_results.append(result)

# Combine calculated results into one list
results = readings + scaled_results + fluxes + extrap_results

# Start writing
writer = bd.Writer(RESULTS_PATH, results)

# Build list of sensor groups, grouped by name
group_dict = dict(
    base="T0cal",
    post="T1cal T2cal T3cal T4cal",
    top="T5cal T6ext",
    water="Tw1cal Tw2cal Tw3cal",
    pressure="Pcal",
    flux="Q12 Q23 Q34 Q45",
)
group = bd.ResultGroup(group_dict, results)

# Add groups of curves to different plot regions
plotter = bd.Plotter("base", group["base"], 0, 0)
plotter.add("post", group["post"], 0, 1)
plotter.add("top", group["top"], 0, 2)
plotter.add("water", group["water"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)
plotter.add("flux", group["flux"], 1, 2)

# Start the write and plot loops
looper = bd.Looper(writer, plotter)

if __name__ == "__main__":
    looper.start()
