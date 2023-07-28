"""Simple test with one sensor."""

from collections import OrderedDict

from boilerdaq import Looper, Plotter, Reading, ResultGroup, Sensor, Writer

sensors_path = "config/test/sensors.csv"
results_path = "results/results.csv"

# Get all readings
all_sensors = Sensor.get(sensors_path)
readings = []
for sensor in all_sensors:
    reading = Reading(sensor)
    readings.append(reading)

# Combine calculated results into one list
results = readings

# Start writing
writer = Writer(results_path, results)

# Build list of sensor groups, grouped by name
group_dict = OrderedDict(
    [
        ("base", "T1"),
    ]
)
group = ResultGroup(group_dict, results)

# Add groups of curves to different plot regions
plotter = Plotter("base", group["base"], 0, 0)

# Start the write and plot loops
looper = Looper(writer, plotter)

if __name__ == "__main__":
    looper.start()
