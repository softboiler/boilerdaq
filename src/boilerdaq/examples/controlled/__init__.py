"""Prepare the feedback-controlled data acquisition loop."""

import boilerdaq as bd
from boilerdaq.examples import (
    BASE_RESULTS,
    CONTROL_SENSOR_NAME,
    CURRENT_LIMIT,
    GROUP_DICT,
    INSTRUMENT,
    OUTPUT_LIMITS,
    POWER_SUPPLIES_PATH,
    RESULTS_PATH,
    SETPOINT,
    START_DELAY,
)

FEEDBACK_SENSOR_NAME = "T0cal"
GAINS = (12, 0.08, 1)

# Get power supply values
all_power_supplies = bd.PowerParam.get(POWER_SUPPLIES_PATH)
power_results = []
for power_supply in all_power_supplies:
    result = bd.PowerResult(power_supply, INSTRUMENT, CURRENT_LIMIT)
    power_results.append(result)
CONTROLLED_RESULTS = power_results + BASE_RESULTS

# Create the writer
WRITER = bd.Writer(RESULTS_PATH, CONTROLLED_RESULTS)
group = bd.ResultGroup(GROUP_DICT, CONTROLLED_RESULTS)

# Create the plotter and add groups of curves to different plot regions
PLOTTER = bd.Plotter("base", group["base"], 0, 0)
PLOTTER.add("post", group["post"], 0, 1)
PLOTTER.add("top", group["top"], 0, 2)
PLOTTER.add("water", group["water"], 1, 0)
PLOTTER.add("pressure", group["pressure"], 1, 1)
PLOTTER.add("flux", group["flux"], 1, 2)

# Create the control loop
CONTROL_SENSOR = bd.Result.get(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS)
CONTROLLER = bd.Controller(
    CONTROL_SENSOR,  # type: ignore
    bd.Result.get(FEEDBACK_SENSOR_NAME, CONTROLLED_RESULTS),
    SETPOINT,
    GAINS,
    OUTPUT_LIMITS,
    START_DELAY,
)

# Create the looper
LOOPER = bd.Looper(WRITER, PLOTTER, CONTROLLER)
