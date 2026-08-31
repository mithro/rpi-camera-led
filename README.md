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

## License

Apache 2.0
