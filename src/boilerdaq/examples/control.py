"""Run the data acquisition and control loop."""

from __future__ import annotations

from csv import DictReader
from pathlib import Path

import pyvisa

import boilerdaq as bd

CONTINUE_FROM_LAST = False

POWER_SUPPLIES_PATH = "config/0_power_supplies.csv"
SENSORS_PATH = "config/1_sensors.csv"
SCALED_PARAMS_PATH = "config/2_scaled_params.csv"
FLUX_PARAMS_PATH = "config/3_flux_params.csv"
EXTRAP_PARAMS_PATH = "config/4_extrap_params.csv"
RESULTS_PATH = "results/results.csv"

BOILING_CURVE_PATH = "notes/curve.csv"

rm = pyvisa.ResourceManager()
VISA_ADDRESS = "USB0::0x0957::0x0807::US25N3188G::0::INSTR"
TERM = "\n"
instrument = rm.open_resource(
    VISA_ADDRESS,
    read_termination=TERM,
    write_termination=TERM,
)

CURRENT_LIMIT = 4
CONTROL_SENSOR_NAME = "V"
FEEDBACK_SENSOR_NAME = "T0cal"
SETPOINT = 30
GAINS = (12, 0.08, 1)
OUTPUT_LIMITS = (0, 300)
START_DELAY = 5

# Get power supply values
all_power_supplies = bd.PowerParam.get(POWER_SUPPLIES_PATH)
power_results = []
for power_supply in all_power_supplies:
    result = bd.PowerResult(power_supply, instrument, CURRENT_LIMIT)
    power_results.append(result)

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
results = power_results + readings + scaled_results + fluxes + extrap_results

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

# Create control loop
control_sensor = bd.Result.get(CONTROL_SENSOR_NAME, results)
controller = bd.Controller(
    control_sensor,  # type: ignore
    bd.Result.get(FEEDBACK_SENSOR_NAME, results),
    SETPOINT,
    GAINS,
    OUTPUT_LIMITS,
    START_DELAY,
)

# Smoothly transition from the last control value
if CONTINUE_FROM_LAST:
    last = sorted(Path(RESULTS_PATH).parent.glob(f"*{Path(RESULTS_PATH).stem}*"))[-1]
    control_source = control_sensor.source
    with last.open() as csv_file:
        reader = DictReader(csv_file)
        last_output = float(
            list(reader)[-1][f"{control_source.name} ({control_source.unit})"]
        )
    controller.pid.set_auto_mode(False)
    controller.pid.set_auto_mode(True, last_output)

# Start the write and plot loops
looper = bd.Looper(writer, plotter, controller)

if __name__ == "__main__":
    looper.start()
