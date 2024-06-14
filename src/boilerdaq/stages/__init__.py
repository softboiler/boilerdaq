"""Prepare the data acquisition loop."""

from boilerdaq.daq import (
    ExtrapParam,
    ExtrapResult,
    Flux,
    FluxParam,
    Plotter,
    Reading,
    ResultGroup,
    ScaledParam,
    ScaledResult,
    Sensor,
)
from boilerdaq.models.params import PARAMS

RESULTS_PATH = PARAMS.paths.results / "results.csv"
CURRENT_LIMIT = 4
CONTROL_SENSOR_NAME = "V"
OUTPUT_LIMITS = (0, 300)

# Build list of sensor groups, grouped by name
GROUP_DICT = dict(
    base="T0cal",
    post="T1cal T2cal T3cal T4cal",
    top="T5cal T6ext",
    water="Tw1cal Tw2cal Tw3cal",
    pressure="Pcal",
    flux="Q12 Q23 Q34 Q45",
)

# Get all readings
all_sensors = Sensor.get(PARAMS.paths.sensors_path)
READINGS = []
for sensor in all_sensors:
    reading = Reading(sensor)
    READINGS.append(reading)

# Get scaled parameters
scaled_params = ScaledParam.get(PARAMS.paths.scaled_params_path)
# Get scaled results
SCALED_RESULTS = []
for param in scaled_params:
    result = ScaledResult(param, READINGS)
    SCALED_RESULTS.append(result)

# Get flux parameters
flux_params = FluxParam.get(PARAMS.paths.flux_params_path)
# Get fluxes
fluxes = []
for param in flux_params:
    result = Flux(param, SCALED_RESULTS)
    fluxes.append(result)

# Get extrapolation parameters
extrap_params = ExtrapParam.get(PARAMS.paths.extrap_params_path)
# Get extrapolated results
extrap_results = []
for param in extrap_params:
    result = ExtrapResult(param, SCALED_RESULTS + fluxes)
    extrap_results.append(result)

BASE_RESULTS = READINGS + SCALED_RESULTS + fluxes + extrap_results

# Build list of sensor groups, grouped by name
group_dict = dict(
    base="T0cal",
    post="T1cal T2cal T3cal T4cal",
    top="T5cal T6ext",
    water="Tw1cal Tw2cal Tw3cal",
    pressure="Pcal",
    flux="Q12 Q23 Q34 Q45",
)
group = ResultGroup(group_dict, BASE_RESULTS)

# Create the plotter and add groups of curves to different plot regions
PLOTTER = Plotter("base", group["base"], 0, 0)
PLOTTER.add("post", group["post"], 0, 1)
PLOTTER.add("top", group["top"], 0, 2)
PLOTTER.add("water", group["water"], 1, 0)
PLOTTER.add("pressure", group["pressure"], 1, 1)
PLOTTER.add("flux", group["flux"], 1, 2)
