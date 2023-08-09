import boilerdaq as bd
from boilerdaq.examples import READINGS, RESULTS_PATH, SCALED_RESULTS

# Combine calculated results into one list
results = READINGS + SCALED_RESULTS
# Start writing
writer = bd.Writer(RESULTS_PATH, results)
# Build list of sensor groups, grouped by name
group_dict = dict(
    uncalibrated="T0 T1 T2 T3 T4 T5 Tw1 Tw2 Tw3 Tw4",
    calibrated="T0cal T1cal T2cal T3cal T4cal T5cal Tw1cal Tw2cal Tw3cal Tw4cal",
    pressure_volts="P",
    pressure="Pcal",
)
group = bd.ResultGroup(group_dict, results)
# Add groups of curves to different plot regions
plotter = bd.Plotter("uncalibrated", group["uncalibrated"], 0, 0)
plotter.add("calibrated", group["calibrated"], 0, 1)
plotter.add("pressure_volts", group["pressure_volts"], 1, 0)
plotter.add("pressure", group["pressure"], 1, 1)
# Start the write and plot loops
looper = bd.Looper(writer, plotter)

if __name__ == "__main__":
    looper.start()
