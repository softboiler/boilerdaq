"""Set the power supply go a given voltage."""

from pyvisa.resources import MessageBasedResource

from boilerdaq.daq import get_result
from boilerdaq.stages.controlled import CONTROLLED_RESULTS

CURRENT_LIMIT = 4
VOLTAGE = 30


def main():  # noqa: D103
    result = get_result("V", CONTROLLED_RESULTS)
    result.open()  # type: ignore
    instrument: MessageBasedResource = result.instrument  # type: ignore
    instrument.write(f"source:current {CURRENT_LIMIT}")
    instrument.write(f"source:voltage {VOLTAGE}")
    instrument.write("output:state on")
    input("Press ENTER to turn off the power supply... ")
    instrument.write("output:state off")
    instrument.write("source:current 0")
    instrument.close()


if __name__ == "__main__":
    main()
