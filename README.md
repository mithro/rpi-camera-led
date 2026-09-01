# RPi Camera LED

Research and design for an LED indicator board that attaches to the Raspberry Pi
camera flex cable (15 pin, 1.0 mm pitch FPC).

## Research

Part availability research comparing [JLCPCB's PCBA parts
library](https://jlcpcb.com/parts) and [NextPCB's Rev0
service](https://www.nextpcb.com/rev0-pcba) (which sources components from [HQ
Online](https://www.hqonline.com/)'s 600k+ in-stock inventory):

* [I2C controllable RGB LEDs](research/i2c-rgb-leds.md)
* [I2C GPIO expanders with LED driving capability](research/i2c-gpio-expanders.md)
* [Cheap (< $0.50) MCUs with I2C and no external parts required](research/cheap-mcus.md)
* [RPi camera compatible FPC connectors (1.0 mm pitch, 15 pin)](research/fpc-connectors.md)

## Hardware

[KiCad schematic](hardware/rpi-camera-led.kicad_sch) ([PDF](hardware/rpi-camera-led.pdf))
for the interposer: two 15-pin FFC connectors passing the camera signals
straight through, with a CH32V003A4M6 (SOP-16) providing I2C-controlled camera
GPIO, PWM illumination LEDs and an ambient light sensor.

Verify it (ERC plus a comparison of the exported netlist against the design
intent) with `uv run hardware/tools/check_schematic.py`, and the board with
`uv run hardware/tools/check_pcb.py`.

J1 and J2 are deliberately different parts — J1 bottom contact, J2 top
contact. The two sit 180° apart on the board so their cables leave opposite
edges, which puts J1 pad *k* opposite J2 pad *16−k*; the top-contact part
flips its cable, so contact *m* really does carry the conductor the Pi calls
*16−m*. That is what lets all fifteen pass-through nets run straight across
instead of crossing the bus, and both checkers enforce it — the schematic one
that the nets pair up, the board one that the pads still physically face each
other. The cost is that the camera-side cable goes in contacts up: use an
opposite-side (type D) FFC there, or fold a standard one.

The schematic is now maintained by hand in eeschema — the connections between
adjacent parts are drawn as wires rather than left implicit in matching global
labels. `hardware/tools/gen_schematic.py` is the generator that bootstrapped it
and is kept in step with the design, but **running it overwrites the schematic**
and would discard that manual wiring.

## License

Apache 2.0
