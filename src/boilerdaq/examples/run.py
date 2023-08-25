"""Run the data acquisition loop."""

from boilerdaq import Looper
from boilerdaq.examples import LOOPER


def main() -> Looper:
    return LOOPER


if __name__ == "__main__":
    main().start()
