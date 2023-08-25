"""Use heat flux as a control parameter."""

import boilercore  # noqa: F401

from boilerdaq import Controller, Looper, get_result
from boilerdaq.examples import CONTROL_SENSOR_NAME, OUTPUT_LIMITS
from boilerdaq.examples.controlled import CONTROLLED_RESULTS, PLOTTER, WRITER

FLUX_SETPOINT = 30
FLUX_FEEDBACK_GAINS = (12, 0.08, 1)
FLUX_FEEDBACK_RESULT_NAME = "flux"


def main() -> Looper:
    control_sensor = get_result(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS)
    controller = Controller(
        control_sensor,  # type: ignore
        get_result(FLUX_FEEDBACK_RESULT_NAME, CONTROLLED_RESULTS),
        FLUX_SETPOINT,
        FLUX_FEEDBACK_GAINS,
        OUTPUT_LIMITS,
    )
    return Looper(WRITER, PLOTTER, controller)


if __name__ == "__main__":
    main().start()
