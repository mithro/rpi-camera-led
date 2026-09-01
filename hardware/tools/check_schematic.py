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

EXPECTED = {
    "GND": {("J1", "1"), ("J1", "4"), ("J1", "7"), ("J1", "10"),
            ("J2", "1"), ("J2", "4"), ("J2", "7"), ("J2", "10"),
            ("U1", "14"), ("C1", "2"), ("C2", "2"), ("Q1", "2"),
            ("R8", "2"), ("R9", "2"), ("J3", "1"), ("J4", "3")},
    "3V3": {("J1", "15"), ("J2", "15"), ("U1", "15"), ("C1", "1"), ("C2", "1"),
            ("R1", "1"), ("R2", "1"), ("R3", "1"), ("R4", "1"),
            ("J3", "2"), ("J4", "1"), ("Q2", "1")},
    "SDA": {("J1", "14"), ("J2", "14"), ("U1", "1"), ("R1", "2"), ("J3", "3")},
    "SCL": {("J1", "13"), ("J2", "13"), ("U1", "2"), ("R2", "2"), ("J3", "4")},
    "CAM_D0_N": {("J1", "2"), ("J2", "2")},
    "CAM_D0_P": {("J1", "3"), ("J2", "3")},
    "CAM_D1_N": {("J1", "5"), ("J2", "5")},
    "CAM_D1_P": {("J1", "6"), ("J2", "6")},
    "CAM_CK_N": {("J1", "8"), ("J2", "8")},
    "CAM_CK_P": {("J1", "9"), ("J2", "9")},
    "PI_IO0": {("J1", "11"), ("R6", "1")},
    "PI_IO1": {("J1", "12"), ("R7", "1")},
    "CAM_IO0": {("J2", "11"), ("U1", "10"), ("R6", "2")},
    "CAM_IO1": {("J2", "12"), ("U1", "13"), ("R7", "2")},
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
# PD4, PD5, PD7/NRST, PA1, PC0.
UNUSED_U1_PINS = {"5", "6", "8", "9", "11", "12", "16"}


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

    # 3. No U1 pin may be forgotten: each is either in a net above or listed
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
