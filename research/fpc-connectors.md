# FPC connectors compatible with the RPi camera cable (1.0 mm pitch, 15 pin)

Availability on both [JLCPCB's PCBA parts library](https://jlcpcb.com/parts) and
[NextPCB's Rev0 service](https://www.nextpcb.com/rev0-pcba) (which sources
components from [HQ Online](https://www.hqonline.com/)'s in-stock inventory).

The standard Raspberry Pi camera cable is a 15-way, 1.0 mm pitch, 0.3 mm thick
FFC with stiffened ends and contacts exposed on one side only. Any 15-position
1.0 mm FFC/FPC connector accepting 0.3 mm cable works mechanically; **pick top-
vs bottom-contact to match which side of the cable faces your board**. The
connector family used on Raspberry Pi boards themselves is Amphenol's SFW15R.

Data collected 2026-09-01 with [`tools/partsearch.py`](tools/partsearch.py);
raw output in [`data/fpc-connectors.jsonl`](data/fpc-connectors.jsonl). Prices
are the **unit price at a quantity of 100** in USD (multiply by 100 for the
cost of 100 units).

## Available on both services

| Product ID | Manufacturer | JLCPCB unit @100 | NextPCB unit @100 | JLCPCB | NextPCB (HQ Online) | Manufacturer page | Datasheet |
|---|---|---|---|---|---|---|---|
| AFA07-S15FCA-00 (bottom contact, slide lock) | JUSHUO (JS) | $0.0940 (6,252 in stock) | $0.0876 (1,634 in stock) | [C262721](https://jlcpcb.com/partdetail/JUSHUO-AFA07_S15FCA00/C262721) | [AFA07-S15FCA-00](https://www.hqonline.com/product-detail/fpc---ffc-connectors-js-afa07-s15fca-00-2500245049) | [jushuo.com](http://www.jushuo.com/)¹ | [PDF (LCSC)](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_JUSHUO-AFA07-S15FCA-00_C262721.pdf) |
| AFA07-S15ECA-00 (top contact, slide lock) | JUSHUO (JS) | $0.1055 (12,866 in stock) | $0.0985 (1,500 in stock) | [C262742](https://jlcpcb.com/partdetail/JUSHUO-AFA07_S15ECA00/C262742) | [AFA07-S15ECA-00](https://www.hqonline.com/product-detail/fpc---ffc-connectors-js-afa07-s15eca-00-2500245070)² | [jushuo.com](http://www.jushuo.com/)¹ | [PDF (LCSC)](https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_JUSHUO-AFA07-S15ECA-00_C262742.pdf) |
| 1.0K-FX-15PWB (bottom contact, slide lock) | HDGC | $0.0933 (**only 3 in stock**) | $0.1296 (**only 5 in stock**) | [C2914074](https://jlcpcb.com/partdetail/HDGC-1_0K_FX15PWB/C2914074) | [1.0K-FX-15PWB](https://www.hqonline.com/product-detail/fpc---ffc-connectors-hdgc-1-0k-fx-15pwb-2500406100) | [hdgc.cn](http://www.hdgc.cn/)¹ | [PDF (LCSC)](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2111021330_HDGC-1-0K-FX-15PWB_C2914074.pdf) |
| FPC-1.0FX-15PWCR-H20 (bottom contact, flip lock) | XUNPU | $0.1510 (3,270 in stock) | $0.1339 (1,440 in stock) | [C19269358](https://jlcpcb.com/partdetail/XUNPU-FPC_1_0FX_15PWCRH20/C19269358) | [FPC-1.0FX-15PWCR-H20](https://www.hqonline.com/product-detail/fpc---ffc-connectors-xunpu-fpc-1-0fx-15pwcr-h20-2500437310) | —¹ | [PDF (LCSC)](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2311211841_XUNPU-FPC-1-0FX-15PWCR-H20_C19269358.pdf) |
| SFW15R-1STE1LF (bottom contact, slide lock) | Amphenol ICC | $0.3893 (5,576 in stock) | $0.3690 (3,962 in stock) | [C3168538](https://jlcpcb.com/partdetail/AmphenolICC-SFW15R1STE1LF/C3168538) | [SFW15R-1STE1LF](https://www.hqonline.com/product-detail/fpc---ffc-connectors-amphenol-sfw15r-1ste1lf-2500434032) | [amphenol-cs.com](https://www.amphenol-cs.com/sfw15r-1ste1lf.html) | [PDF (Amphenol drawing)](https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/sfw15r-1ste1lf.pdf)³ |

All are right-angle (horizontal) SMD, 1.0 mm pitch, 15 position, for 0.3 mm
FFC.

¹ The budget connector makers have no per-part web pages: JUSHUO and HDGC only
have corporate sites, and XUNPU's site (xunpu.com) failed TLS when checked, so
the LCSC-hosted datasheets are the authoritative document links.
² HQ Online also carries a CAX-branded clone,
[AFA07-S15ECA-00-H2.5](https://www.hqonline.com/product-detail/fpc---ffc-connectors-cax-afa07-s15eca-00-h2-5-2500419281)
at $0.0642 (180 in stock).
³ The Amphenol CDN rejects non-browser clients (HTTP 403); the link works in a
browser.

## Near misses (JLCPCB only, not stocked by HQ Online)

| Product ID | Manufacturer | JLCPCB unit @100 | Notes |
|---|---|---|---|
| [SFW15R-2STE1LF](https://jlcpcb.com/partdetail/AmphenolICC-SFW15R2STE1LF/C3167933) | Amphenol ICC | $0.8385 (only 44 in stock) | Dual-contact variant — the exact part used on Raspberry Pi boards |
| [HC-FPC-1.0-15P-FHH20](https://jlcpcb.com/partdetail/HongCheng-HC_FPC_1_0_15PFHH20/C49166884) | Hong Cheng | $0.1647 (1,401 in stock) | Dual contact, flip lock — accepts the cable either way up |
| [HC-FPC-1.0-15P-CXH25](https://jlcpcb.com/partdetail/HongCheng-HC_FPC_1_0_15PCXH25/C49166850) | Hong Cheng | $0.0777 (1,103 in stock) | Bottom contact, slide lock — cheapest 15P option on JLCPCB |
| [1.0K-GT-15PB](https://jlcpcb.com/partdetail/HDGC-1_0K_GT15PB/C2915527) | HDGC | $0.1228 (2,998 in stock) | Vertical-entry slide lock, like the Pi's own connector orientation |
| [HC-FPC-1.0-15P-LH25](https://jlcpcb.com/partdetail/HongCheng-HC_FPC_1_0_15PLH25/C49166919) | Hong Cheng | $0.1155 (607 in stock) | Vertical-entry slide lock |

## Recommendation

**AFA07-S15FCA-00 / AFA07-S15ECA-00** (~$0.09–0.11, deep stock on both
services) are the pragmatic choice — pick the F (bottom) or E (top) contact
variant once the board's mounting orientation is decided. If you want the
name-brand part with the highest mating-cycle spec and the same footprint as
the Pi ecosystem, **SFW15R-1STE1LF** costs ~4× more but is also comfortably
stocked on both services.
