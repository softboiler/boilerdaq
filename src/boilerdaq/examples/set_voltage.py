"""Set a voltage on the power supply."""


from time import sleep

import pyvisa

CURRENT_LIMIT = 4
VOLTAGE = 0
DELAY = 2
TERM = "\n"

rm = pyvisa.ResourceManager()
inst = rm.open_resource(
    "USB0::0x0957::0x0807::US25N3188G::0::INSTR",
    # query_delay=DELAY,
    read_termination=TERM,
    write_termination=TERM,
)

inst.write(f"source:current {CURRENT_LIMIT}")
inst.write(f"source:voltage {VOLTAGE}")
inst.write("output:state on")

sleep(5)
# input("Press ENTER to turn off the power supply... ")

inst.write("output:state off")
inst.write("source:current 0")
inst.close()
