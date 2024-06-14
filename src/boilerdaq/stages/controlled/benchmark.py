"""Run a benchmark prior to experimentation."""

from boilerdaq.daq import Controller, Looper, Writer, get_result
from boilerdaq.models.params import PARAMS
from boilerdaq.stages import CONTROL_SENSOR_NAME, OUTPUT_LIMITS
from boilerdaq.stages.controlled import CONTROLLED_RESULTS, PLOTTER

RESULTS_PATH = PARAMS.paths.benchmarks / "benchmark.csv"
TEMP_SETPOINT = 30
TEMP_FEEDBACK_GAINS = (12, 0.08, 1)
TEMP_FEEDBACK_SENSOR_NAME = "T0cal"


def main() -> Looper:  # noqa: D103
    writer = Writer(RESULTS_PATH, CONTROLLED_RESULTS)
    control_sensor = get_result(CONTROL_SENSOR_NAME, CONTROLLED_RESULTS)
    controller = Controller(
        control_sensor,  # type: ignore
        get_result(TEMP_FEEDBACK_SENSOR_NAME, CONTROLLED_RESULTS),
        TEMP_SETPOINT,
        TEMP_FEEDBACK_GAINS,
        OUTPUT_LIMITS,
    )
    return Looper(writer, PLOTTER, controller)


if __name__ == "__main__":
    main().start()
