"""Run a benchmark prior to experimentation."""

import boilerdaq as bd
from boilerdaq.examples.controlled import CONTROLLED_RESULTS, CONTROLLER, PLOTTER

results_path = "results/benchmark.csv"
writer = bd.Writer(results_path, CONTROLLED_RESULTS)
looper = bd.Looper(writer, PLOTTER, CONTROLLER)

if __name__ == "__main__":
    looper.start()
