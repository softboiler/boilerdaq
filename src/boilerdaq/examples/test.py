"""Simple test with one sensor."""

from boilerdaq import Looper, Plotter, ResultGroup, Writer
from boilerdaq.examples import READINGS, RESULTS_PATH

# Combine calculated results into one list
results = READINGS
# Start writing
writer = Writer(RESULTS_PATH, READINGS)
# Build list of sensor groups, grouped by name
group_dict = dict(base="T1")
group = ResultGroup(group_dict, READINGS)
# Add groups of curves to different plot regions
plotter = Plotter("base", group["base"], 0, 0)
# Start the write and plot loops
looper = Looper(writer, plotter)

if __name__ == "__main__":
    looper.start()
