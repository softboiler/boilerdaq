"""Prepare the feedback-controlled data acquisition loop."""

import boilerdaq as bd
from boilerdaq.examples import (
    BASE_RESULTS,
    CURRENT_LIMIT,
    GROUP_DICT,
    INSTRUMENT,
    POWER_SUPPLIES_PATH,
    RESULTS_PATH,
)

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
