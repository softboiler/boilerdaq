"""Prepare the feedback-controlled data acquisition loop."""

from boilerdaq import INSTRUMENT
from boilerdaq.daq import Plotter, PowerParam, PowerResult, ResultGroup, Writer
from boilerdaq.models.params import PARAMS
from boilerdaq.stages import BASE_RESULTS, CURRENT_LIMIT, GROUP_DICT, RESULTS_PATH

# Get power supply values
all_power_supplies = PowerParam.get(PARAMS.paths.power_supplies_path)
power_results = []
for power_supply in all_power_supplies:
    result = PowerResult(power_supply, INSTRUMENT, CURRENT_LIMIT)
    power_results.append(result)
CONTROLLED_RESULTS = power_results + BASE_RESULTS

# Create the writer
writer = Writer(RESULTS_PATH, CONTROLLED_RESULTS)
group = ResultGroup(GROUP_DICT, CONTROLLED_RESULTS)

# Create the plotter and add groups of curves to different plot regions
PLOTTER = Plotter("base", group["base"], 0, 0)
PLOTTER.add("post", group["post"], 0, 1)
PLOTTER.add("top", group["top"], 0, 2)
PLOTTER.add("water", group["water"], 1, 0)
PLOTTER.add("pressure", group["pressure"], 1, 1)
PLOTTER.add("flux", group["flux"], 1, 2)
