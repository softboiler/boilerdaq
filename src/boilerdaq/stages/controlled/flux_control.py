"""Use heat flux as a control parameter."""

import boilercore  # noqa: F401

from boilerdaq.daq import (
    Controller,
    FitResult,
    Looper,
    Plotter,
    Result,
    ResultGroup,
    Writer,
    get_result,
)
from boilerdaq.stages import CONTROL_SENSOR_NAME, OUTPUT_LIMITS, RESULTS_PATH
from boilerdaq.stages.controlled import CONTROLLED_RESULTS

FLUX_SETPOINT = 5
FLUX_FEEDBACK_GAINS = (12, 0.08, 1)
FLUX_FEEDBACK_RESULT_NAME = "flux"


def main() -> Looper:
    fit_result = FitResult(
        FLUX_FEEDBACK_RESULT_NAME,
        "W/cm^2",
        [
            get_result(result, CONTROLLED_RESULTS)
            for result in "T1cal T2cal T3cal T4cal T5cal".split()
        ],
    )
    results: list[Result] = [*CONTROLLED_RESULTS, fit_result]
    controller = Controller(
        get_result(CONTROL_SENSOR_NAME, results),
        fit_result,
        FLUX_SETPOINT,
        FLUX_FEEDBACK_GAINS,
        OUTPUT_LIMITS,
    )
    group_dict = dict(
        feedback=FLUX_FEEDBACK_RESULT_NAME,
        post="T1cal T2cal T3cal T4cal",
        top="T5cal T6ext",
        water="Tw1cal Tw2cal Tw3cal",
        pressure="Pcal",
        flux="Q12 Q23 Q34 Q45",
    )
    group = ResultGroup(group_dict, results)
    plotter = Plotter("feedback", group["feedback"], 0, 0)
    plotter.add("post", group["post"], 0, 1)
    plotter.add("top", group["top"], 0, 2)
    plotter.add("water", group["water"], 1, 0)
    plotter.add("pressure", group["pressure"], 1, 1)
    plotter.add("flux", group["flux"], 1, 2)
    return Looper(Writer(RESULTS_PATH, results), plotter, controller)


if __name__ == "__main__":
    main().start()
