"""Use heat flux as a control parameter."""

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
from boilerdaq.models.params import PARAMS
from boilerdaq.stages import CONTROL_SENSOR_NAME, OUTPUT_LIMITS, RESULTS_PATH
from boilerdaq.stages.controlled import CONTROLLED_RESULTS

FLUX_SETPOINT = 2
FLUX_FEEDBACK_GAINS = (12, 0.08, 1)
FLUX_FEEDBACK_RESULT_NAME = "q_s"
FLUX_FEEDBACK_RESULT_UNIT = "W/cm^2"


def main() -> Looper:
    fit_result = FitResult(
        name=FLUX_FEEDBACK_RESULT_NAME,
        unit="W/cm^2",
        fit=PARAMS.fit,
        model=PARAMS.paths.model,
        results_to_fit=[
            get_result(name=result, results=CONTROLLED_RESULTS)
            for result in "T1cal T2cal T3cal T4cal T5cal".split()
        ],
    )
    results: list[Result] = [*CONTROLLED_RESULTS, fit_result]
    controller = Controller(
        control_result=get_result(name=CONTROL_SENSOR_NAME, results=results),
        feedback_result=fit_result,
        setpoint=FLUX_SETPOINT,
        gains=FLUX_FEEDBACK_GAINS,
        output_limits=OUTPUT_LIMITS,
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
