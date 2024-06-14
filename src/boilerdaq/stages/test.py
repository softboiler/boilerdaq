"""Simple test with one sensor."""

from boilerdaq.daq import Looper, Plotter, ResultGroup, Writer
from boilerdaq.stages import READINGS, RESULTS_PATH

GROUP_DICT = dict(base="T1")


def main() -> Looper:  # noqa: D103
    writer = Writer(RESULTS_PATH, READINGS)
    group = ResultGroup(GROUP_DICT, READINGS)
    plotter = Plotter("base", group["base"], 0, 0)
    return Looper(writer, plotter)


if __name__ == "__main__":
    main().start()
