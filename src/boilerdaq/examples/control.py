"""Run the data acquisition and control loop."""

from __future__ import annotations

from csv import DictReader
from pathlib import Path

import boilerdaq as bd
from boilerdaq import (
    CONTINUE_FROM_LAST,
    CONTROL_SENSOR_NAME,
    CURRENT_LIMIT,
    INSTRUMENT,
    OUTPUT_LIMITS,
    POWER_SUPPLIES_PATH,
    RESULTS_PATH,
    SETPOINT,
    START_DELAY,
)
from boilerdaq.examples import BASE_RESULTS

FEEDBACK_SENSOR_NAME = "T0cal"
GAINS = (12, 0.08, 1)
# Get power supply values
all_power_supplies = bd.PowerParam.get(POWER_SUPPLIES_PATH)
power_results = []
for power_supply in all_power_supplies:
    result = bd.PowerResult(power_supply, INSTRUMENT, CURRENT_LIMIT)
    power_results.append(result)
results = power_results + BASE_RESULTS

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
