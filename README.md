# RPi Camera LED

An interposer for the Raspberry Pi camera flex cable (15 pin, 1.0 mm pitch FPC).
It sits in the middle of the cable, passes all fifteen camera signals straight
through, and adds a CH32V003A4M6 that gives the Pi I2C-controlled camera GPIO,
PWM illumination LEDs and an ambient light reading.

## Hardware

[KiCad schematic](hardware/rpi-camera-led.kicad_sch) ·
[PDF](hardware/rpi-camera-led.pdf) ·
[board](hardware/rpi-camera-led.kicad_pcb)

### Board: 15-way FFC camera interposer

| 3D render, top | 3D render, bottom | Layout (copper, silk, outline) |
|:--------------:|:-----------------:|:------------------------------:|
| <img src="docs/img/board-3d-top.png" alt="Interposer, front side" width="300"> | <img src="docs/img/board-3d-bottom.png" alt="Interposer, back side" width="300"> | <img src="docs/img/board-layout.svg" alt="Interposer copper layout" width="300"> |

25.0 × 23.9 mm, two layers, everything on the front. J1 (left) faces the
Raspberry Pi and J2 (right) faces the camera; they sit 180° apart so the two
cable segments leave opposite edges and the board drops into an existing cable
run in line. The MCU is the SOIC-16 in the middle, the two white illumination
LEDs and the phototransistor are along the top edge.

**The layout is in progress**, in two respects.

Eleven of the twenty footprints — C1, C2, J3, J4, Q1, R1–R4, R8 and R9 — are
still parked outside the board outline, which is why they float around the
board in the renders. The fifteen-way pass-through bus is routed; the rest is
not. DRC currently reports 116 violations and 35 unconnected items.

And both connectors are turned the wrong way round. Their backs are flush with
the board edges (J1's housing ends at x = 20.000, J2's at x = 45.000, against
an outline of 20.0–45.0), which puts both **mouths facing each other across the
middle of the board**, 14.4 mm apart. The cables would have to enter from the
board's interior, through the space the MCU occupies. Each needs rotating 180°
so its mouth faces its own board edge — which moves the pads, so the routed bus
has to be redone with it.

Regenerate the three images above with `uv run hardware/tools/render_board.py`,
and the connector models with `uv run hardware/tools/gen_connector_model.py`.

### Connectors, and which cables fit

J1 and J2 are **not** the same part, and that is deliberate:

| | part | contacts | mates with |
|---|---|---|---|
| **J1** → Raspberry Pi | JUSHUO AFA07-S15**F**CA-00 (LCSC C262721) | **bottom** — cable copper faces the board | a standard Pi camera cable |
| **J2** → camera | JUSHUO AFA07-S15**E**CA-00 (LCSC C262742) | **top** — cable copper faces away | a standard Pi camera cable |

The reason is cable parity. A Raspberry Pi camera cable is an *opposite-side*
FFC — "type 2", contacts on one face at one end and the other face at the other
— because the Pi's CSI socket is top-contact and the camera module's is
bottom-contact. Cutting one continuous cable anywhere yields one same-side half
and one opposite-side half, so an interposer whose two connectors want the
copper on the *same* face forces one odd, hard-to-buy cable. One that wants it
on *opposite* faces absorbs the asymmetry, and both segments become ordinary
Raspberry Pi camera cables. Bottom-contact at J1 plus top-contact at J2 is that
pairing.

The two variants share one land pattern — verified against both JUSHUO drawings
— so nothing on the board moves between them. Since only the contact side
differs, and it is invisible on an assembled board, the distinction is called
out in each symbol's value, in the MPN, and as a `BOTTOM CONTACT` / `TOP
CONTACT` marker on the fab layer.

Both footprints and their 3D models live in this repository, in
`hardware/rpi-camera-led.pretty` and `hardware/rpi-camera-led.3dshapes`. KiCad's
stock footprint references a STEP file for the JUSHUO AFA07 series that does not
exist — not in the KiCad distribution and not in `kicad-packages3D` upstream,
which ships no JUSHUO models at all. Third-party libraries have one, but under
terms that forbid redistribution, so `hardware/tools/gen_connector_model.py`
builds it from the manufacturer's published drawing instead: a 22.00 × 6.95 ×
2.50 mm envelope matching the drawing's DIM D, the F.Fab outline and the side
view's height, with the housing and latch coloured as the drawing's notes
specify. Both STEP and WRL are generated, the latter in the 0.1-inch units
KiCad expects.

The pass-through bus is wired J1 pin *k* ↔ J2 pin *16−k*. That looks reversed
but is exactly right: the two connectors are 180° apart, so J1 pad *k*
physically faces J2 pad *16−k*, and joining the pads that face each other is
both the straight route and the electrically transparent one — the board
behaves as a splice in the middle of one continuous cable.
`check_pcb.py` measures that facing alignment as a number, because losing it to
a stray drag puts a dogleg in all fifteen nets and is invisible by eye.

### Verifying

```
uv run hardware/tools/check_schematic.py   # ERC + netlist vs design intent
uv run hardware/tools/check_pcb.py         # connector alignment + DRC parity
```

`check_schematic.py` currently **fails**: its expected-netlist table still
describes the older pin-for-pin bus, and four issues from the last eeschema
session are open — U1 pin 13 is unconnected, SWIO and CAM_IO1 have been merged
onto one net, I2C is landed on pins that cannot carry it on this package (the
CH32V003 SOP-16 reaches the peripheral only on pins 1 and 2, since both AFIO
remaps need PD0 or PC5 and the package bonds out neither), and four no-connect
flags dangle.

The schematic is maintained by hand in eeschema — connections between adjacent
parts are drawn as wires rather than left implicit in matching global labels.
`hardware/tools/gen_schematic.py` is the generator that bootstrapped it, but
**running it overwrites the schematic** and would discard that manual wiring.

## Firmware

[CH32V003 firmware](firmware/README.md): a fail-safe I2C bootloader plus an
application exposing camera GPIO control, RPi-side GPIO readback, GPIO
pass-through, LED brightness (hardware PWM) and an ambient light reading over
a Linux-friendly SMBus register map at address 0x42. Builds with
`riscv64-unknown-elf-gcc` and [ch32v003fun](https://github.com/cnlohr/ch32v003fun)
(`git submodule update --init`, then `make` in `firmware/bootloader` and
`firmware/app`).

The firmware still targets the older pin map and needs updating to match the
current schematic.

## Research

Part availability research comparing [JLCPCB's PCBA parts
library](https://jlcpcb.com/parts) and [NextPCB's Rev0
service](https://www.nextpcb.com/rev0-pcba) (which sources components from [HQ
Online](https://www.hqonline.com/)'s 600k+ in-stock inventory):

* [I2C controllable RGB LEDs](research/i2c-rgb-leds.md)
* [I2C GPIO expanders with LED driving capability](research/i2c-gpio-expanders.md)
* [Cheap (< $0.50) MCUs with I2C and no external parts required](research/cheap-mcus.md)
* [RPi camera compatible FPC connectors (1.0 mm pitch, 15 pin)](research/fpc-connectors.md)

## License

Apache 2.0 — see [LICENSE](LICENSE).
