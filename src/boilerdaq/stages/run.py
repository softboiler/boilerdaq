"""Run the data acquisition loop."""

from boilerdaq.daq import Looper, Writer
from boilerdaq.stages import BASE_RESULTS, PLOTTER, RESULTS_PATH


def main() -> Looper:  # noqa: D103
    return Looper(Writer(RESULTS_PATH, BASE_RESULTS), PLOTTER)


if __name__ == "__main__":
    main().start()
