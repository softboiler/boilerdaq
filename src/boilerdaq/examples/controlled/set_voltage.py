"""Set the power supply go a given voltage."""

from pyvisa.resources import MessageBasedResource

from boilerdaq import get_result
from boilerdaq.examples.controlled import CONTROLLED_RESULTS

_CURRENT_LIMIT = 4
_VOLTAGE = 0

instrument: MessageBasedResource = get_result("V", CONTROLLED_RESULTS).instrument  # type: ignore
instrument.write(f"source:current {_CURRENT_LIMIT}")
instrument.write(f"source:voltage {_VOLTAGE}")
instrument.write("output:state on")
input("Press ENTER to turn off the power supply... ")
instrument.write("output:state off")
instrument.write("source:current 0")
instrument.close()
