"""Run the data acquisition and control loop."""

from __future__ import annotations

import boilerdaq as bd
from boilerdaq import (
    EXTRAP_PARAMS_PATH,
    FLUX_PARAMS_PATH,
    SCALED_PARAMS_PATH,
    SENSORS_PATH,
)

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

BASE_RESULTS = readings + scaled_results + fluxes + extrap_results
