"""Add exact purchasing fields to populated symbols in the schematic.

Run from the repository root. The schematic remains the BOM source of truth.
"""

from pathlib import Path
import re
from urllib.parse import quote_plus

SCH = Path(__file__).resolve().parent.parent / "rpi-camera-led.kicad_sch"

PARTS = {
    "C1": ("100nF", "Murata", "GRM155R71A104KA01D", "C71687",
           "100 nF, 0402, X7R, 10 V, ±10%"),
    "C2": ("1uF", "Murata", "GRM155R61A105KE15D", "C105172",
           "1 uF, 0402, X5R, 10 V, ±10%"),
    "D1": ("White LED", "Foshan NationStar Optoelectronics",
           "NCD0805W1", "C110099",
           "White LED, 0805, 20 mA, 2.6-3.6 V, 130° viewing angle"),
    "D2": ("White LED", "Foshan NationStar Optoelectronics",
           "NCD0805W1", "C110099",
           "White LED, 0805, 20 mA, 2.6-3.6 V, 130° viewing angle"),
    "J1": ("FFC 15P 1.0mm bottom contact (to Raspberry Pi)", "JUSHUO",
           "AFA07-S15FCA-00", "C262721",
           "15-position, 1.0 mm pitch, SMT, bottom-contact FFC connector"),
    "J2": ("FFC 15P 1.0mm top contact (to camera)", "JUSHUO",
           "AFA07-S15ECA-00", "C262742",
           "15-position, 1.0 mm pitch, SMT, top-contact FFC connector"),
    "J3": ("Qwiic (JST SH 1.0mm)", "JST",
           "SM04B-SRSS-TB", "C160404",
           "4-position, 1.0 mm pitch, side-entry SMT connector"),
    "J4": ("SWD program header 2.54mm", "Sullins Connector Solutions",
           "PBC03SAAN", "C3333754",
           "3-position, 2.54 mm pitch, vertical through-hole male header"),
    "Q1": ("AO3400A", "Alpha & Omega Semiconductor", "AO3400A", "C20917",
           "N-channel MOSFET, 30 V, SOT-23"),
    "Q2": ("Phototransistor", "Vishay", "TEMT7000X01", "C499538",
           "Visible/near-IR silicon phototransistor, 0805, top-view"),
    "R1": ("4.7k", "Yageo", "RC0402FR-074K7L", "C105871",
           "4.7 kΩ, 0402, 1%, 62.5 mW"),
    "R2": ("4.7k", "Yageo", "RC0402FR-074K7L", "C105871",
           "4.7 kΩ, 0402, 1%, 62.5 mW"),
    "R3": ("47R", "Yageo", "RC0603FR-0747RL", "C114623",
           "47 Ω, 0603, 1%, 100 mW LED current limiter"),
    "R4": ("47R", "Yageo", "RC0603FR-0747RL", "C114623",
           "47 Ω, 0603, 1%, 100 mW LED current limiter"),
    "R5": ("100R", "Yageo", "RC0402FR-07100RL", "C106232",
           "100 Ω, 0402, 1%, 62.5 mW"),
    "R8": ("10k", "Yageo", "RC0402FR-0710KL", "C137965",
           "10 kΩ, 0402, 1%, 62.5 mW"),
    "R9": ("47k", "Yageo", "RC0402FR-0747KL", "C93943",
           "47 kΩ, 0402, 1%, 62.5 mW"),
    "U1": ("CH32V003A4M6", "WCH", "CH32V003A4M6", "C5346357",
           "32-bit RISC-V microcontroller, SOP-16, 16 KiB flash"),
}


def sexp_end(text, start):
    depth = 0
    in_string = False
    i = start
    while i < len(text):
        char = text[i]
        if in_string:
            if char == "\\":
                i += 2
                continue
            if char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced schematic s-expression")


def quote(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def set_property(block, name, value, anchor):
    pattern = re.compile(rf'(\(property "{re.escape(name)}" ")[^"]*(")')
    replacement = rf'\g<1>{quote(value)}\g<2>'
    if pattern.search(block):
        return pattern.sub(replacement, block, count=1)
    x, y = anchor
    field = (
        f'\t\t(property "{name}" "{quote(value)}"\n'
        f'\t\t\t(at {x} {y} 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n'
        '\t\t)\n'
    )
    pin = re.search(r"(?m)^\t\t\(pin ", block)
    if not pin:
        raise ValueError(f"no pin block found while adding {name}")
    return block[:pin.start()] + field + block[pin.start():]


def main():
    text = SCH.read_text(encoding="utf-8")
    matches = list(re.finditer(r"(?m)^\t\(symbol\n", text))
    found = set()
    for match in reversed(matches):
        end = sexp_end(text, match.start())
        block = text[match.start():end]
        reference = re.search(r'\(property "Reference" "([^"]+)"', block)
        if not reference or reference.group(1) not in PARTS:
            continue
        ref = reference.group(1)
        value, manufacturer, mpn, lcsc, description = PARTS[ref]
        origin = re.search(r"\(at ([-\d.]+) ([-\d.]+) [-\d.]+\)", block)
        if not origin:
            raise ValueError(f"no symbol origin found for {ref}")
        fields = {
            "Value": value,
            "Manufacturer": manufacturer,
            "MPN": mpn,
            "LCSC": lcsc,
            "Description": description,
            "DigiKey": (
                "https://www.digikey.com/en/products/result?keywords="
                + quote_plus(mpn)
            ),
            "Mouser": "https://www.mouser.com/c/?q=" + quote_plus(mpn),
        }
        for name, field_value in fields.items():
            block = set_property(block, name, field_value, origin.groups())
        text = text[:match.start()] + block + text[end:]
        found.add(ref)
    missing = set(PARTS) - found
    if missing:
        raise ValueError(f"could not locate schematic symbols: {sorted(missing)}")
    SCH.write_text(text, encoding="utf-8", newline="")
    print(f"Sourced {len(found)} populated symbols in {SCH}")


if __name__ == "__main__":
    main()
