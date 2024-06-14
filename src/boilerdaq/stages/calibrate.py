"""Calibrate thermocouples."""

from boilerdaq.daq import Looper, Plotter, ResultGroup, Writer
from boilerdaq.stages import READINGS, RESULTS_PATH, SCALED_RESULTS

# Build list of sensor groups, grouped by name
GROUP_DICT = dict(
    uncalibrated="T0 T1 T2 T3 T4 T5 Tw1 Tw2 Tw3 Tw4",
    calibrated="T0cal T1cal T2cal T3cal T4cal T5cal Tw1cal Tw2cal Tw3cal Tw4cal",
    pressure_volts="P",
    pressure="Pcal",
)


def main() -> Looper:  # noqa: D103
    # Combine calculated results into one list
    results = READINGS + SCALED_RESULTS
    # Start writing
    writer = Writer(RESULTS_PATH, results)
    group = ResultGroup(GROUP_DICT, results)
    # Add groups of curves to different plot regions
    plotter = Plotter("uncalibrated", group["uncalibrated"], 0, 0)
    plotter.add("calibrated", group["calibrated"], 0, 1)
    plotter.add("pressure_volts", group["pressure_volts"], 1, 0)
    plotter.add("pressure", group["pressure"], 1, 1)
    # Start the write and plot loops
    return Looper(writer, plotter)


if __name__ == "__main__":
    main().start()
