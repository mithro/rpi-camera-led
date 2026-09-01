# Cheap MCUs (< $0.50) with I2C and no external parts required

Availability on both [JLCPCB's PCBA parts library](https://jlcpcb.com/parts) and
[NextPCB's Rev0 service](https://www.nextpcb.com/rev0-pcba) (which sources
components from [HQ Online](https://www.hqonline.com/)'s in-stock inventory).

Requirements applied: unit price under $0.50 at 100 pieces on **both**
services, internal flash, internal RC oscillator, internal power-on reset
(i.e. runs with nothing but supply decoupling), and a hardware I2C peripheral.

Data collected 2026-09-01 with [`tools/partsearch.py`](tools/partsearch.py);
raw output in [`data/cheap-mcus.jsonl`](data/cheap-mcus.jsonl). Prices are the
**unit price at a quantity of 100** in USD (multiply by 100 for the cost of
100 units).

## Available on both services

| Product ID | Manufacturer | JLCPCB unit @100 | NextPCB unit @100 | JLCPCB | NextPCB (HQ Online) | Manufacturer page | Datasheet |
|---|---|---|---|---|---|---|---|
| PY32F002AW15U6TR (QFN-16) | Puya | $0.1606 (34,614 in stock) | $0.1499 (400 in stock) | [C5291740](https://jlcpcb.com/partdetail/PUYA-PY32F002AW15U6TR/C5291740) | [PY32F002AW15U6TR](https://www.hqonline.com/product-detail/8-bit-mcu-microcontrollers-puya-py32f002aw15u6tr-2500438827) | [py32.org](https://py32.org/en/mcu/PY32F002Axx)¹ | [PDF (LCSC)](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2303271200_PUYA--PY32F002AW15U6TR_C5291740.pdf) |
| CH32V003J4M6 (SOP-8) | WCH | $0.1845 (29,690 in stock) | $0.1722 (858 in stock) | [C5346354](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH32V003J4M6/C5346354) | [CH32V003J4M6](https://www.hqonline.com/product-detail/32-bit-mcu-microcontrollers-wch-ch32v003j4m6-2500409955) | [wch-ic.com](https://www.wch-ic.com/products/CH32V003.html) | [PDF (WCH)](https://www.wch-ic.com/downloads/CH32V003DS0_PDF.html) |
| STC8G1K08-36I-SOP8 | STC Micro | $0.1966 (3,585 in stock) | $0.1835 (577 in stock) | [C713818](https://jlcpcb.com/partdetail/STCMicro-STC8G1K08_36ISOP8/C713818)² | [STC8G1K08-36I-SOP8](https://www.hqonline.com/product-detail/32-bit-mcu-microcontrollers-stc-stc8g1k08-36i-sop8-2500336185) | [stcmicro.com](https://www.stcmicro.com/stc/stc8g1k08.html) | [PDF (STC, STC8G family)](https://www.stcmicro.com/datasheet/STC8G-en.pdf) |
| CH32V003A4M6 (SOP-16) | WCH | $0.2151 (2,117 in stock) | $0.2008 (100 in stock) | [C5346357](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH32V003A4M6/C5346357) | [CH32V003A4M6](https://www.hqonline.com/product-detail/32-bit-mcu-microcontrollers-wch-ch32v003a4m6-2500439164) | [wch-ic.com](https://www.wch-ic.com/products/CH32V003.html) | [PDF (WCH)](https://www.wch-ic.com/downloads/CH32V003DS0_PDF.html) |
| CH32V006F8U7 (QFN-20) | WCH | $0.2174 (2,915 in stock) | $0.1957 (1,950 in stock) | [C55112440](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH32V006F8U7/C55112440) | [CH32V006F8U7](https://www.hqonline.com/product-detail/32-bit-mcu-microcontrollers-wch-ch32v006f8u7-1046732864) | [wch-ic.com](https://www.wch-ic.com/products/CH32V006.html) | [PDF (WCH)](https://www.wch-ic.com/downloads/CH32V006DS0_PDF.html) |
| CH32V003F4P6 (TSSOP-20) | WCH | $0.2237 (12,635 in stock) | $0.2088 (3,951 in stock) | [C5187096](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH32V003F4P6/C5187096) | [CH32V003F4P6](https://www.hqonline.com/product-detail/32-bit-mcu-microcontrollers-wch-ch32v003f4p6-2500421881) | [wch-ic.com](https://www.wch-ic.com/products/CH32V003.html) | [PDF (WCH)](https://www.wch-ic.com/downloads/CH32V003DS0_PDF.html) |
| PY32F030K28T6 (LQFP-32) | Puya | $0.4185 (1,391 in stock) | $0.3947 (100 in stock) | [C3018720](https://jlcpcb.com/partdetail/PUYA-PY32F030K28T6/C3018720) | [PY32F030K28T6](https://www.hqonline.com/product-detail/8-bit-mcu-microcontrollers-puya-py32f030k28t6-2500438830) | [puyasemi.com](https://www.puyasemi.com/en/py32f030.html) | [PDF (LCSC)](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2205171716_PUYA--PY32F030K28T6_C3018720.pdf) |

¹ Puya's own English site no longer lists the PY32F002A series (checked
2026-09-01: it does not appear in the PY32-series navigation at
[puyasemi.com/en/py32_series.html](https://www.puyasemi.com/en/py32_series.html));
[py32.org](https://py32.org/en/mcu/PY32F002Axx) (OpenPuya) is the best
persistent documentation page.

² JLCPCB stocks this MPN twice; [C18208924](https://jlcpcb.com/partdetail/STCMicro-STC8G1K08_36ISOP8/C18208924)
is $0.1893 with 30,889 in stock. The A-variant
[STC8G1K08A-36I-SOP8, C915663](https://jlcpcb.com/partdetail/STCMicro-STC8G1K08A_36ISOP8/C915663)
($0.2136, 96,225 in stock) is JLCPCB-only.

Family notes:

* **CH32V003** (RISC-V RV32EC, 48 MHz, 16 KB flash / 2 KB RAM, internal 24 MHz
  RC, 1× I2C) — the same die in SOP-8 / SOP-16 / TSSOP-20 / QFN-20; the QFN-20
  ([C5299908](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH32V003F4U6/C5299908),
  $0.2527, 5,000 in stock) was not found on HQ Online. Programmed via WCH's
  1-wire SWIO (needs a WCH-LinkE).
* **CH32V006** (RV32EmC, 48 MHz, 62 KB flash / 8 KB RAM) — newer CH32V003
  successor, also single-wire debug.
* **PY32F002A** (Cortex-M0+, 24 MHz, 20 KB flash / 3 KB RAM, internal 24 MHz
  RC, 1× I2C) — programmed via standard SWD, works with ordinary ST-Link/DAP
  probes and the community [py32.org](https://py32.org/) toolchain. HQ Online
  also stocks SOP-8 (PY32F002AL15S6TU, $0.1482) and TSSOP-20
  (PY32F002AF15P6TU, $0.1544) variants, but JLCPCB had those package variants
  at 0 stock, so only the QFN-16 overlaps.
* **STC8G1K08** (1T 8051, up to 36 MHz internal RC, 8 KB flash, hardware I2C)
  — programmed over UART with a bootloader, no probe needed at all.
* **PY32F030** (Cortex-M0+, 48 MHz, 64 KB flash / 8 KB RAM) — the "big"
  option, still under $0.50 on both.

All of the above run from their internal oscillator with internal POR and
BOR — the only external parts required are supply decoupling capacitors.

## Recommendation

For an I2C peripheral device on a camera LED board, **CH32V003J4M6** (SOP-8)
or **PY32F002AW15U6TR** (QFN-16) are the sweet spot at ~$0.15–0.21 on both
services with five-digit JLCPCB stock. Choose PY32F002A if standard SWD
programming matters; choose CH32V003 for the larger community (ch32fun etc.)
and easier-to-solder SOP-8. Note the CH32V003's I2C slave mode is
well-supported in ch32fun examples.
