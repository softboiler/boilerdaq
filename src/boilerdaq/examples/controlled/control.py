"""Run the data acquisition and control loop."""

from boilerdaq import Controller, Looper, get_result
from boilerdaq.examples import CONTROL_SENSOR_NAME, OUTPUT_LIMITS
from boilerdaq.examples.controlled import CONTROLLED_RESULTS, PLOTTER, WRITER

TEMP_SETPOINT = 30
TEMP_FEEDBACK_GAINS = (12, 0.08, 1)
TEMP_FEEDBACK_SENSOR_NAME = "T0cal"


def main() -> Looper:
    control_sensor = get_result(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS)
    controller = Controller(
        control_sensor,  # type: ignore
        get_result(TEMP_FEEDBACK_SENSOR_NAME, CONTROLLED_RESULTS),
        TEMP_SETPOINT,
        TEMP_FEEDBACK_GAINS,
        OUTPUT_LIMITS,
    )
    return Looper(WRITER, PLOTTER, controller)


if __name__ == "__main__":
    main().start()
