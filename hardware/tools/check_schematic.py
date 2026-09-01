# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Verify hardware/rpi-camera-led.kicad_sch: run KiCad's ERC and compare the
exported netlist against the design intent.

Usage (from the repository root):
    uv run hardware/tools/check_schematic.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
SCH = HW / "rpi-camera-led.kicad_sch"
KICAD_CLI = "/snap/bin/kicad.kicad-cli"

# J2 is the top-contact part, so its cable goes in flipped and contact m
# carries what the Pi side calls pin 16-m.  That is also what lets the bus
# route straight: on the board J1 and J2 sit 180 degrees apart, so J1 pad k
# lines up with J2 pad 16-k.  See PASS_THROUGH below, which checks it.
EXPECTED = {
    "GND": {("J1", "1"), ("J1", "4"), ("J1", "7"), ("J1", "10"),
            ("J2", "15"), ("J2", "12"), ("J2", "9"), ("J2", "6"),
            ("U1", "14"), ("C1", "2"), ("C2", "2"), ("Q1", "2"),
            ("R8", "2"), ("R9", "2"), ("J3", "1"), ("J4", "3")},
    "3V3": {("J1", "15"), ("J2", "1"), ("U1", "15"), ("C1", "1"), ("C2", "1"),
            ("R1", "1"), ("R2", "1"), ("R3", "1"), ("R4", "1"),
            ("J3", "2"), ("J4", "1"), ("Q2", "1")},
    "SDA": {("J1", "14"), ("J2", "2"), ("U1", "1"), ("R1", "2"), ("J3", "3")},
    "SCL": {("J1", "13"), ("J2", "3"), ("U1", "2"), ("R2", "2"), ("J3", "4")},
    "CAM_D0_N": {("J1", "2"), ("J2", "14")},
    "CAM_D0_P": {("J1", "3"), ("J2", "13")},
    "CAM_D1_N": {("J1", "5"), ("J2", "11")},
    "CAM_D1_P": {("J1", "6"), ("J2", "10")},
    "CAM_CK_N": {("J1", "8"), ("J2", "8")},
    "CAM_CK_P": {("J1", "9"), ("J2", "7")},
    # U1 straddles each GPIO channel rather than sharing a pin with the link:
    # PD5/PD6 watch the Pi side, PA1/PA2 drive the camera side.
    "PI_IO0": {("J1", "11"), ("R6", "1"), ("U1", "10")},
    "PI_IO1": {("J1", "12"), ("R7", "1"), ("U1", "9")},
    "CAM_IO0": {("J2", "5"), ("U1", "12"), ("R6", "2")},
    "CAM_IO1": {("J2", "4"), ("U1", "13"), ("R7", "2")},
    # SOP-16 frees the LED from the debug pin: PD1 is now programming only,
    # and PC3 (TIM1 CH3) drives the gate resistor.
    "SWIO": {("U1", "7"), ("J4", "2")},
    "LED_PWM": {("U1", "3"), ("R5", "1")},
    "LED_GATE": {("R5", "2"), ("Q1", "1"), ("R8", "1")},
    "LED1_A": {("R3", "2"), ("D1", "2")},
    "LED2_A": {("R4", "2"), ("D2", "2")},
    "LED_SW": {("D1", "1"), ("D2", "1"), ("Q1", "3")},
    "LIGHT_SENSE": {("U1", "4"), ("Q2", "2"), ("R9", "1")},
}

# SOP-16 pins with nothing on them (no_connect in the schematic): PC6, PC7,
# PD4, PD7 and PC0.  PD7 is deliberately left alone: it is the NRST pin until
# the RST_MODE option byte in flash says otherwise, so wiring a Pi GPIO to it
# would let the Pi reset the MCU on a factory-fresh part.
UNUSED_U1_PINS = {"5", "6", "8", "11", "16"}

# J1 and J2 sit 180 degrees apart on the board (cables leave opposite edges),
# so J1 pad k is physically opposite J2 pad 16-k.  Every pass-through net must
# join such a pair or it cannot be a straight trace -- this is the whole reason
# J2 is the top-contact part.  The two GPIO channels reach the far connector
# through the R6/R7 links rather than directly, so they pair up by name.
COUPLED = {("PI_IO0", "CAM_IO0"), ("PI_IO1", "CAM_IO1")}


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
    return r


def main():
    ok = True

    # 1. ERC
    erc_path = HW / "erc.json"
    r = run(KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all",
            "-o", str(erc_path), str(SCH))
    report = json.loads(erc_path.read_text())
    issues = [
        f"  [{v['severity']}] {v['type']}: {v['description']}"
        for s in report.get("sheets", [])
        for v in s.get("violations", [])
    ]
    print(f"ERC: {len(issues)} violation(s)")
    for line in issues:
        print(line)
    if any("[error]" in i for i in issues):
        ok = False
    erc_path.unlink()

    # 2. Netlist comparison
    net_path = HW / "netcheck.net"
    run(KICAD_CLI, "sch", "export", "netlist", "-o", str(net_path), str(SCH))
    text = net_path.read_text()
    nets = {}
    blocks = re.split(r'\(net \(code "\d+"\) \(name "', text)[1:]
    for block in blocks:
        name = block[: block.index('"')]
        pins = set(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block))
        nets[name.lstrip("/")] = pins
    net_path.unlink()

    pin_net = {pin: name for name, pins in nets.items() for pin in pins}

    for name, want in EXPECTED.items():
        got = nets.pop(name, set())
        if got != want:
            ok = False
            print(f"NET MISMATCH {name}:")
            print(f"  missing: {sorted(want - got)}")
            print(f"  extra:   {sorted(got - want)}")
    for name, pins in nets.items():
        if len(pins) > 1:
            ok = False
            print(f"UNEXPECTED NET {name}: {sorted(pins)}")

    # 3. Every pass-through net must join pads that face each other, or the
    #    bus cannot route straight across.
    for k in range(1, 16):
        a = pin_net.get(("J1", str(k)))
        b = pin_net.get(("J2", str(16 - k)))
        if a is None or b is None:
            ok = False
            print(f"PASS-THROUGH J1.{k}/J2.{16 - k}: "
                  f"pin not on any net (J1={a}, J2={b})")
        elif a != b and (a, b) not in COUPLED:
            ok = False
            print(f"PASS-THROUGH J1.{k} ({a}) does not face J2.{16 - k} ({b})"
                  " -- this net would have to cross the bus")

    # 4. No U1 pin may be forgotten: each is either in a net above or listed
    #    as deliberately unused.  Catches a pin silently dropped on a repackage.
    wired = {p for pins in EXPECTED.values() for (ref, p) in pins if ref == "U1"}
    overlap = wired & UNUSED_U1_PINS
    missed = {str(i) for i in range(1, 17)} - wired - UNUSED_U1_PINS
    if overlap or missed:
        ok = False
        if overlap:
            print(f"U1 pins both wired and marked unused: {sorted(overlap)}")
        if missed:
            print(f"U1 pins unaccounted for: {sorted(missed, key=int)}")
    print("netlist:", "matches design intent" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
