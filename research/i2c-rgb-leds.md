# I2C controllable RGB LEDs

Availability on both [JLCPCB's PCBA parts library](https://jlcpcb.com/parts) and
[NextPCB's Rev0 service](https://www.nextpcb.com/rev0-pcba) (which sources
components from [HQ Online](https://www.hqonline.com/)'s in-stock inventory).

Data collected 2026-09-01 with [`tools/partsearch.py`](tools/partsearch.py);
raw output in [`data/i2c-rgb-leds.jsonl`](data/i2c-rgb-leds.jsonl). Prices are
the **unit price at a quantity of 100** in USD (multiply by 100 for the cost of
100 units).

## Key finding

**Neither library stocks an RGB LED package with I2C built into the LED
itself.** The "smart RGB LED" packages both services stock (WS2812B, SK6812,
XL-1010RGBC etc.) all use single-wire or SPI-like protocols, not I2C. The
practical way to get an I2C-controlled RGB LED is an I2C RGB LED
*controller/driver IC* plus a plain RGB LED, so the parts below are I2C RGB LED
controller ICs (all have per-channel PWM intended for driving an RGB LED
directly).

## Available on both services

| Product ID | Manufacturer | JLCPCB unit @100 | NextPCB unit @100 | JLCPCB | NextPCB (HQ Online) | Manufacturer page | Datasheet |
|---|---|---|---|---|---|---|---|
| AW2023DNR | Awinic | $0.1849 (3,750 in stock) | $0.1726 (500 in stock) | [C401014](https://jlcpcb.com/partdetail/385728-AW2023DNR/C401014) | [AW2023DNR](https://www.hqonline.com/product-detail/led-lighting-drivers-awinic-aw2023dnr-2500438352) | [awinic.com](https://www.awinic.com/en/productDetail/AW2023DNR) | [PDF (LCSC)](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2004081212_AWINIC-Shanghai-Awinic-Tech-AW2023DNR_C401014.pdf) |
| LP5562TMX/NOPB | Texas Instruments | $0.3958 (1,817 in stock) | $2.8697 (20 in stock) | [C544465](https://jlcpcb.com/partdetail/TexasInstruments-LP5562TMXNOPB/C544465) | [LP5562TMX/NOPB](https://www.hqonline.com/product-detail/led-lighting-drivers-ti-lp5562tmx-nopb-1017504026) | [ti.com](https://www.ti.com/product/LP5562) | [PDF (TI)](https://www.ti.com/lit/ds/symlink/lp5562.pdf) |
| LP5009RUKR | Texas Instruments | $0.4623 (2,568 in stock) | $0.4382 (100 in stock) | [C701960](https://jlcpcb.com/partdetail/TexasInstruments-LP5009RUKR/C701960) | [LP5009RUKR](https://www.hqonline.com/product-detail/led-lighting-drivers-ti-lp5009rukr-2500432488) | [ti.com](https://www.ti.com/product/LP5009) | [PDF (TI)](https://www.ti.com/lit/ds/symlink/lp5009.pdf) |
| IS31FL3199-QFLS2-TR | Lumissil (ISSI) | $0.5807 (1,125 in stock) | $0.6807 (292 in stock) | [C150408](https://jlcpcb.com/partdetail/161746-IS31FL3199_QFLS2TR/C150408) | [IS31FL3199-QFLS2-TR](https://www.hqonline.com/product-detail/led-lighting-drivers-issi-is31fl3199-qfls2-tr-2500412294) | [lumissil.com](https://www.lumissil.com/productsdetail/IS31FL3199.html) | [PDF (Lumissil)](https://www.lumissil.com/assets/pdf/core/IS31FL3199_DS.pdf) |
| LP5024RSMR | Texas Instruments | $0.9358 (6,748 in stock) | $0.8871 (50 in stock) | [C427525](https://jlcpcb.com/partdetail/TexasInstruments-LP5024RSMR/C427525) | [LP5024RSMR](https://www.hqonline.com/product-detail/led-lighting-drivers-ti-lp5024rsmr-2500440883) | [ti.com](https://www.ti.com/product/LP5024) | [PDF (TI)](https://www.ti.com/lit/ds/symlink/lp5024.pdf) |

Channel counts: AW2023 and LP5562 drive 3 channels (LP5562 has 4, RGB+W);
LP5009 drives 9, IS31FL3199 drives 9, LP5024 drives 24 — i.e. 3, 3 and 8 RGB
LEDs respectively.

## Near misses (JLCPCB only, not stocked by HQ Online)

| Product ID | Manufacturer | JLCPCB unit @100 | Notes |
|---|---|---|---|
| [AW2013DNR](https://jlcpcb.com/partdetail/247622-AW2013DNR/C252440) | Awinic | $0.1557 (6,907 in stock) | 3-ch, predecessor of AW2023 |
| [BCT3253EGG-TR](https://jlcpcb.com/partdetail/BROADCHIP-BCT3253EGGTR/C2961994) | Broadchip | $0.0855 (2,385 in stock) | 3-ch, cheapest option; WLCSP-12 package is hard to hand-rework |
| [IS31FL3193-DLS2-TR](https://jlcpcb.com/partdetail/2745272-IS31FL3193_DLS2TR/C2653363) | Lumissil (ISSI) | $0.5271 (6,112 in stock) | 3-ch |
| [KTD2026EWE-TR](https://jlcpcb.com/partdetail/KINETIC-KTD2026EWETR/C500368) | Kinetic | $0.4071 (only 9 in stock) | 3-ch |
| [NCP5623CMUTBG](https://jlcpcb.com/partdetail/onsemi-NCP5623CMUTBG/C892560) | onsemi | $0.3487 (0 in stock) | 3-ch with charge pump |
| [SGM31324YUDW8G/TR](https://jlcpcb.com/partdetail/SGMICRO-SGM31324YUDW8GTR/C699917) | SGMicro | $0.1833 (0 in stock) | 3-ch |

## Recommendation

**AW2023DNR** is the standout: cheapest of the parts on both services, healthy
stock on both, 3 independent 25 mA current-sink channels with autonomous
breathing/pattern engines, I2C up to 400 kHz, 2.5–5.5 V supply. Its caveat is
the DFN-10-EP (2×2 mm) package. If more LEDs are wanted later, LP5009 (3× RGB)
or LP5024 (8× RGB) scale up while staying available on both services.
