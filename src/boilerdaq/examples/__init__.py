"""Prepare the data acquisition loop."""

from pyvisa import ResourceManager

import boilerdaq as bd

POWER_SUPPLIES_PATH = "config/0_power_supplies.csv"
RESULTS_PATH = "results/results.csv"
CURRENT_LIMIT = 4
CONTROL_SENSOR_NAME = "V"
SETPOINT = 30
OUTPUT_LIMITS = (0, 300)
START_DELAY = 5
INSTRUMENT = ResourceManager().open_resource(
    "USB0::0x0957::0x0807::US25N3188G::0::INSTR",
    read_termination="\n",
    write_termination="\n",
)

sensors_path = "config/1_sensors.csv"
scaled_params_path = "config/2_scaled_params.csv"
flux_params_path = "config/3_flux_params.csv"
extrap_params_path = "config/4_extrap_params.csv"

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
all_sensors = bd.Sensor.get(sensors_path)
READINGS = []
for sensor in all_sensors:
    reading = bd.Reading(sensor)
    READINGS.append(reading)

# Get scaled parameters
scaled_params = bd.ScaledParam.get(scaled_params_path)
# Get scaled results
SCALED_RESULTS = []
for param in scaled_params:
    result = bd.ScaledResult(param, READINGS)
    SCALED_RESULTS.append(result)

# Get flux parameters
flux_params = bd.FluxParam.get(flux_params_path)
# Get fluxes
fluxes = []
for param in flux_params:
    result = bd.Flux(param, SCALED_RESULTS)
    fluxes.append(result)

# Get extrapolation parameters
extrap_params = bd.ExtrapParam.get(extrap_params_path)
# Get extrapolated results
extrap_results = []
for param in extrap_params:
    result = bd.ExtrapResult(param, SCALED_RESULTS + fluxes)
    extrap_results.append(result)

BASE_RESULTS = READINGS + SCALED_RESULTS + fluxes + extrap_results

# Create the writer
WRITER = bd.Writer(RESULTS_PATH, BASE_RESULTS)

# Build list of sensor groups, grouped by name
group_dict = dict(
    base="T0cal",
    post="T1cal T2cal T3cal T4cal",
    top="T5cal T6ext",
    water="Tw1cal Tw2cal Tw3cal",
    pressure="Pcal",
    flux="Q12 Q23 Q34 Q45",
)
group = bd.ResultGroup(group_dict, BASE_RESULTS)

# Create the plotter and add groups of curves to different plot regions
plotter = bd.Plotter("base", group["base"], 0, 0)
plotter.add("post", group["post"], 0, 1)
plotter.add("top", group["top"], 0, 2)
plotter.add("water", group["water"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)
plotter.add("flux", group["flux"], 1, 2)

# Create the looper
LOOPER = bd.Looper(WRITER, plotter)
