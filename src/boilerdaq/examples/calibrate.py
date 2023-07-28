from __future__ import annotations

import boilerdaq as bd

sensors_path = "config/1_sensors.csv"
scaled_params_path = "config/2_scaled_params.csv"
results_path = "results/results.csv"

# Get all readings
all_sensors = bd.Sensor.get(sensors_path)
readings = []
for sensor in all_sensors:
    reading = bd.Reading(sensor)
    readings.append(reading)

# Get scaled parameters
scaled_params = bd.ScaledParam.get(scaled_params_path)
# Get scaled results
scaled_results = []
for param in scaled_params:
    result = bd.ScaledResult(param, readings)
    scaled_results.append(result)

# Combine calculated results into one list
results = readings + scaled_results

# Start writing
writer = bd.Writer(results_path, results)

# Build list of sensor groups, grouped by name
group_dict = dict(
    uncalibrated="T0 T1 T2 T3 T4 T5 Tw1 Tw2 Tw3 Tw4",
    calibrated="T0cal T1cal T2cal T3cal T4cal T5cal Tw1cal Tw2cal Tw3cal Tw4cal",
    pressure_volts="P",
    pressure="Pcal",
)
group = bd.ResultGroup(group_dict, results)

# Add groups of curves to different plot regions
plotter = bd.Plotter("uncalibrated", group["uncalibrated"], 0, 0)
plotter.add("calibrated", group["calibrated"], 0, 1)
plotter.add("pressure_volts", group["pressure_volts"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)


# Start the write and plot loops
looper = bd.Looper(writer, plotter)

if __name__ == "__main__":
    looper.start()
