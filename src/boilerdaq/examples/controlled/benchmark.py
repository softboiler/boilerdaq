"""Run a benchmark prior to experimentation."""

import boilerdaq as bd
from boilerdaq.examples.controlled import CONTROLLED_RESULTS, CONTROLLER, PLOTTER

RESULTS_PATH = "results/benchmark.csv"
WRITER = bd.Writer(RESULTS_PATH, CONTROLLED_RESULTS)
LOOPER = bd.Looper(WRITER, PLOTTER, CONTROLLER)

if __name__ == "__main__":
    LOOPER.start()
