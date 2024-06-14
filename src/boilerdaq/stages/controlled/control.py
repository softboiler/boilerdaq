"""Run the data acquisition and control loop."""

from boilerdaq.daq import Controller, Looper, Writer, get_result
from boilerdaq.stages import CONTROL_SENSOR_NAME, OUTPUT_LIMITS, RESULTS_PATH
from boilerdaq.stages.controlled import CONTROLLED_RESULTS, PLOTTER

TEMP_SETPOINT = 30
TEMP_FEEDBACK_GAINS = (12, 0.08, 1)
TEMP_FEEDBACK_SENSOR_NAME = "T0cal"


def main() -> Looper:  # noqa: D103
    controller = Controller(
        get_result(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS),  # type: ignore
        get_result(TEMP_FEEDBACK_SENSOR_NAME, CONTROLLED_RESULTS),
        TEMP_SETPOINT,
        TEMP_FEEDBACK_GAINS,
        OUTPUT_LIMITS,
    )
    return Looper(Writer(RESULTS_PATH, CONTROLLED_RESULTS), PLOTTER, controller)


if __name__ == "__main__":
    main().start()
