# I2C GPIO expanders with LED driving capability

Availability on both [JLCPCB's PCBA parts library](https://jlcpcb.com/parts) and
[NextPCB's Rev0 service](https://www.nextpcb.com/rev0-pcba) (which sources
components from [HQ Online](https://www.hqonline.com/)'s in-stock inventory).

Data collected 2026-09-01 with [`tools/partsearch.py`](tools/partsearch.py);
raw output in [`data/i2c-gpio-expanders.jsonl`](data/i2c-gpio-expanders.jsonl).
Prices are the **unit price at a quantity of 100** in USD (multiply by 100 for
the cost of 100 units).

## Available on both services

| Product ID | Manufacturer | JLCPCB unit @100 | NextPCB unit @100 | JLCPCB | NextPCB (HQ Online) | Manufacturer page | Datasheet |
|---|---|---|---|---|---|---|---|
| AW9523BTQR | Awinic | $0.2659 (59,674 in stock) | $0.2482 (5,584 in stock) | [C148077](https://jlcpcb.com/partdetail/159410-AW9523BTQR/C148077) | [AW9523BTQR](https://www.hqonline.com/product-detail/i-o-expanders-awinic-aw9523btqr-2500442592) | [awinic.com](https://www.awinic.com/en/productDetail/AW9523BTQR) | [PDF (LCSC)](https://www.lcsc.com/datasheet/lcsc_datasheet_1809192237_AWINIC-Shanghai-Awinic-Tech-AW9523BTQR_C148077.pdf) |
| CH423S | WCH | $0.3084 (2,528 in stock) | $0.2907 (267 in stock) | [C111663](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH423S/C111663) | [CH423S](https://www.hqonline.com/product-detail/i-o-expanders-wch-ch423s-2500352610) | [wch-ic.com](https://www.wch-ic.com/products/CH423.html) | [PDF (WCH)](https://www.wch-ic.com/downloads/CH423DS1_PDF.html) |
| PCA9685PW,118 | NXP | $1.9625 (888 in stock) | $1.8418 (only 7 in stock) | [C2678753](https://jlcpcb.com/partdetail/NXPSemicon-PCA9685PW118/C2678753) | [PCA9685PW,118](https://www.hqonline.com/product-detail/led-lighting-drivers-nxp-pca9685pw-118-2500218737) | [nxp.com](https://www.nxp.com/products/PCA9685) | [PDF (NXP)](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf) |

Capability summary:

* **AW9523BTQR** — 16 GPIO, every pin selectable between GPIO mode and a
  256-step current-dimmed LED mode (up to 37 mA sink per pin), interrupt
  output, 4 I2C addresses, TQFN-24 (4×4 mm). The classic "GPIO expander that
  is also an LED driver".
* **CH423S** — 8 bidirectional GPIO + 16 open-drain outputs designed for LED
  segment/matrix scan driving, SOP-28. No per-pin PWM/current control.
* **PCA9685PW** — 16 channels of 12-bit PWM intended for LED control (25 mA
  sink per output); it is an LED controller rather than a true GPIO expander
  (outputs only). Note HQ Online only had 7 pieces in stock.

## Near misses (JLCPCB only, not stocked by HQ Online)

| Product ID | Manufacturer | JLCPCB unit @100 | Notes |
|---|---|---|---|
| [AW9110BTQR](https://jlcpcb.com/partdetail/247625-AW9110BTQR/C252443) | Awinic | $0.2936 (0 in stock) | 10-pin version of AW9523B |
| [AW9106BTQR](https://jlcpcb.com/partdetail/247630-AW9106BTQR/C252448) | Awinic | $0.2498 (0 in stock) | 6-pin version of AW9523B |
| [TLC59108IPWR](https://jlcpcb.com/partdetail/TexasInstruments-TLC59108IPWR/C130031) | Texas Instruments | $1.2440 (1,708 in stock) | 8-ch 8-bit PWM LED driver |
| [PCA9632DP1,118](https://jlcpcb.com/partdetail/NXPSemicon-PCA9632DP1118/C2802665) | NXP | $1.6543 (only 15 in stock) | 4-ch PWM LED driver |
| [PCA9955BTWJ](https://jlcpcb.com/partdetail/NXPSemicon-PCA9955BTWJ/C2678563) | NXP | $1.9381 (138 in stock) | 16-ch constant-current LED driver |

## Recommendation

**AW9523BTQR** is the clear winner for this project: deep stock on both
services, ~$0.25–0.27 at 100 pieces, and its LED mode does exactly the
"expander that drives LEDs" job — 16 pins is enough for 5 RGB LEDs with
per-channel 256-step dimming, no MCU firmware needed.
