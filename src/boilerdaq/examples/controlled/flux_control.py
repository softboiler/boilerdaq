"""Use heat flux as a control parameter."""

import boilercore  # noqa: F401

import boilerdaq as bd
from boilerdaq.examples import CONTROL_SENSOR_NAME, OUTPUT_LIMITS
from boilerdaq.examples.controlled import CONTROLLED_RESULTS, PLOTTER, WRITER

FLUX_SETPOINT = 30
FLUX_FEEDBACK_GAINS = (12, 0.08, 1)
FLUX_FEEDBACK_RESULT_NAME = "flux"

# Create the control loop
CONTROL_SENSOR = bd.get_result(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS)
controller = bd.Controller(
    CONTROL_SENSOR,  # type: ignore
    bd.get_result(FLUX_FEEDBACK_RESULT_NAME, CONTROLLED_RESULTS),
    FLUX_SETPOINT,
    FLUX_FEEDBACK_GAINS,
    OUTPUT_LIMITS,
)

looper = bd.Looper(WRITER, PLOTTER, controller)

if __name__ == "__main__":
    looper.start()
