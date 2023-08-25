"""Prepare the data acquisition loop."""

from boilerdaq import (
    ExtrapParam,
    ExtrapResult,
    Flux,
    FluxParam,
    Looper,
    Plotter,
    Reading,
    ResultGroup,
    ScaledParam,
    ScaledResult,
    Sensor,
    Writer,
)

_SENSORS_PATH = "config/1_sensors.csv"
_SCALED_PARAMS_PATH = "config/2_scaled_params.csv"
_FLUX_PARAMS_PATH = "config/3_flux_params.csv"
_EXTRAP_PARAMS_PATH = "config/4_extrap_params.csv"

POWER_SUPPLIES_PATH = "config/0_power_supplies.csv"
RESULTS_PATH = "results/results.csv"

INSTRUMENT = "USB0::0x0957::0x0807::US25N3188G::0::INSTR"
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
all_sensors = Sensor.get(_SENSORS_PATH)
READINGS = []
for sensor in all_sensors:
    reading = Reading(sensor)
    READINGS.append(reading)

# Get scaled parameters
scaled_params = ScaledParam.get(_SCALED_PARAMS_PATH)
# Get scaled results
SCALED_RESULTS = []
for param in scaled_params:
    result = ScaledResult(param, READINGS)
    SCALED_RESULTS.append(result)

# Get flux parameters
flux_params = FluxParam.get(_FLUX_PARAMS_PATH)
# Get fluxes
fluxes = []
for param in flux_params:
    result = Flux(param, SCALED_RESULTS)
    fluxes.append(result)

# Get extrapolation parameters
extrap_params = ExtrapParam.get(_EXTRAP_PARAMS_PATH)
# Get extrapolated results
extrap_results = []
for param in extrap_params:
    result = ExtrapResult(param, SCALED_RESULTS + fluxes)
    extrap_results.append(result)

BASE_RESULTS = READINGS + SCALED_RESULTS + fluxes + extrap_results

# Create the writer
WRITER = Writer(RESULTS_PATH, BASE_RESULTS)

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
plotter = Plotter("base", group["base"], 0, 0)
plotter.add("post", group["post"], 0, 1)
plotter.add("top", group["top"], 0, 2)
plotter.add("water", group["water"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)
plotter.add("flux", group["flux"], 1, 2)

# Create the looper
LOOPER = Looper(WRITER, plotter)
