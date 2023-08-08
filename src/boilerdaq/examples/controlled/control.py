"""Run the data acquisition and control loop."""

from csv import DictReader
from pathlib import Path

from boilerdaq.examples import RESULTS_PATH
from boilerdaq.examples.controlled import CONTROL_SENSOR, CONTROLLER, LOOPER

CONTINUE_FROM_LAST = False

# Smoothly transition from the last control value
if CONTINUE_FROM_LAST:
    last = sorted(Path(RESULTS_PATH).parent.glob(f"*{Path(RESULTS_PATH).stem}*"))[-1]
    control_source = CONTROL_SENSOR.source
    with last.open() as csv_file:
        reader = DictReader(csv_file)
        last_output = float(
            list(reader)[-1][f"{control_source.name} ({control_source.unit})"]
        )
    CONTROLLER.pid.set_auto_mode(False)
    CONTROLLER.pid.set_auto_mode(True, last_output)


if __name__ == "__main__":
    LOOPER.start()
