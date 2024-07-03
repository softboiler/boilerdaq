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

SURFACE_TEMP_SETPOINT = 30
PID_GAINS = (12, 0.08, 1)
SURFACE_TEMP = "T_s"
SURFACE_TEMP_UNIT = "C"


def main(surface_temp_setpoint: float = SURFACE_TEMP_SETPOINT):  # noqa: D103
    looper(surface_temp_setpoint).start()


def looper(surface_temp_setpoint: float = SURFACE_TEMP_SETPOINT) -> Looper:  # noqa: D103
    fit_result = FitResult(
        name=SURFACE_TEMP,
        unit=SURFACE_TEMP_UNIT,
        fit=PARAMS.fit,
        models=PARAMS.paths.models,
        results_to_fit=[
            get_result(name=result, results=CONTROLLED_RESULTS)
            for result in "T1cal T2cal T3cal T4cal T5cal".split()
        ],
    )
    results: list[Result] = [*CONTROLLED_RESULTS, fit_result]
    controller = Controller(
        control_result=get_result(name=CONTROL_SENSOR_NAME, results=results),
        feedback_result=fit_result,
        setpoint=surface_temp_setpoint,
        gains=PID_GAINS,
        output_limits=OUTPUT_LIMITS,
    )
    group_dict = dict(
        feedback=SURFACE_TEMP,
        post="T1cal T2cal T3cal T4cal",
        top="T5cal",
        control="V",
        water="Tw1cal Tw2cal Tw3cal",
        pressure="Pcal",
    )
    group = ResultGroup(group_dict, results)
    plotter = Plotter("feedback", group["feedback"], 0, 0)
    plotter.add("post", group["post"], 0, 1)
    plotter.add("top", group["top"], 0, 2)
    plotter.add("control", group["control"], 1, 0)
    plotter.add("water", group["water"], 1, 1)
    plotter.add("pressure", group["pressure"], 1, 2)
    return Looper(Writer(RESULTS_PATH, results), plotter, controller)


if __name__ == "__main__":
    main()
