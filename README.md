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
straight through, with a CH32V003J4M6 providing I2C-controlled camera GPIO,
PWM illumination LEDs and an ambient light sensor. Regenerate with
`uv run hardware/tools/gen_schematic.py` and verify (ERC + netlist vs design
intent) with `uv run hardware/tools/check_schematic.py`.

## Firmware

[CH32V003 firmware](firmware/README.md): a fail-safe I2C bootloader plus an
application exposing camera GPIO control, RPi-side GPIO readback, GPIO
pass-through, LED brightness (hardware PWM) and an ambient light reading over
a Linux-friendly SMBus register map at address 0x42. Builds with
`riscv64-unknown-elf-gcc` and [ch32v003fun](https://github.com/cnlohr/ch32v003fun)
(`git submodule update --init`, then `make` in `firmware/bootloader` and
`firmware/app`).

## License

Apache 2.0
