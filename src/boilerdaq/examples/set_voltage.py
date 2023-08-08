"""Set a voltage on the power supply."""

# Due to 'inst.write'  # pyright 1.1.317
# pyright: reportGeneralTypeIssues=none

from boilerdaq.examples import INSTRUMENT

_CURRENT_LIMIT = 4
_VOLTAGE = 0
INSTRUMENT.write(f"source:current {_CURRENT_LIMIT}")
INSTRUMENT.write(f"source:voltage {_VOLTAGE}")
INSTRUMENT.write("output:state on")
input("Press ENTER to turn off the power supply... ")
INSTRUMENT.write("output:state off")
INSTRUMENT.write("source:current 0")
INSTRUMENT.close()
