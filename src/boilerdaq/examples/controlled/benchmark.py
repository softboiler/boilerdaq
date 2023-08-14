"""Run a benchmark prior to experimentation."""

import boilerdaq as bd
from boilerdaq.examples import CONTROL_SENSOR_NAME, OUTPUT_LIMITS
from boilerdaq.examples.controlled import CONTROLLED_RESULTS, PLOTTER

results_path = "results/benchmark.csv"
temp_setpoint = 30
temp_feedback_gains = (12, 0.08, 1)
temp_feedback_sensor_name = "T0cal"
writer = bd.Writer(results_path, CONTROLLED_RESULTS)

# Create the control loop
CONTROL_SENSOR = bd.get_result(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS)
controller = bd.Controller(
    CONTROL_SENSOR,  # type: ignore
    bd.get_result(temp_feedback_sensor_name, CONTROLLED_RESULTS),
    temp_setpoint,
    temp_feedback_gains,
    OUTPUT_LIMITS,
)

looper = bd.Looper(writer, PLOTTER, controller)

if __name__ == "__main__":
    looper.start()
