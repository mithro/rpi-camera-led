# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Verify hardware/rpi-camera-led.kicad_pcb: the connectors stay aligned so the
pass-through bus can route straight, and the board still matches the schematic.

The J1/J2 alignment is easy to lose to a stray drag and expensive to notice --
a 0.05mm slip puts a dogleg in all fifteen nets -- so it is checked as a number
rather than by eye.

Usage (from the repository root):
    uv run hardware/tools/check_pcb.py
"""

import json
import math
import re
import subprocess
import sys
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
PCB = HW / "rpi-camera-led.kicad_pcb"
KICAD_CLI = "/snap/bin/kicad.kicad-cli"

TOL = 0.001  # mm; anything above this is a real misalignment, not rounding


def sexp_end(text, start):
    depth, in_str, i = 0, False, start
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced s-expression")


def footprints(text):
    """reference -> {pad number: [(x, y), ...]} in board coordinates."""
    out = {}
    for m in re.finditer(r'\(footprint "([^"]+)"', text):
        block = text[m.start():sexp_end(text, m.start())]
        ref = re.search(r'\(property "Reference" "([^"]*)"', block)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", block)
        if not (ref and at):
            continue
        ox, oy = float(at.group(1)), float(at.group(2))
        th = math.radians(float(at.group(3) or 0))
        cos, sin = math.cos(th), math.sin(th)
        pads = {}
        for pm in re.finditer(
            r'\(pad "([^"]+)"\s+\w+\s+\w+\s*\n?\s*\(at ([-\d.]+) ([-\d.]+)', block
        ):
            px, py = float(pm.group(2)), float(pm.group(3))
            pads.setdefault(pm.group(1), []).append(
                (ox + px * cos + py * sin, oy - px * sin + py * cos)
            )
        out[ref.group(1)] = pads
    return out


def board_centre_x(text):
    xs = []
    for m in re.finditer(r"\(gr_\w+\b", text):
        block = text[m.start():sexp_end(text, m.start())]
        if '"Edge.Cuts"' not in block:
            continue
        xs += [float(p) for p, _ in
               re.findall(r"\((?:start|end|mid) ([-\d.]+) ([-\d.]+)\)", block)]
    return (min(xs) + max(xs)) / 2 if xs else None


def main():
    ok = True
    text = PCB.read_text()
    fps = footprints(text)

    # 1. Every pass-through pair must face across at the same Y.  J1 and J2 sit
    #    180 degrees apart, so J1 pad k is opposite J2 pad 16-k.
    j1, j2 = fps.get("J1"), fps.get("J2")
    if not (j1 and j2):
        print("J1 or J2 missing from the board")
        return 1
    worst, worst_at = 0.0, None
    for k in range(1, 16):
        a, b = j1.get(str(k)), j2.get(str(16 - k))
        if not (a and b):
            ok = False
            print(f"PAD MISSING: J1.{k} or J2.{16 - k}")
            continue
        dy = abs(a[0][1] - b[0][1])
        if dy > worst:
            worst, worst_at = dy, (k, 16 - k)
    print(f"connector alignment: worst |dY| {worst:.6f} mm"
          + (f" at J1.{worst_at[0]}/J2.{worst_at[1]}" if worst_at else ""))
    if worst > TOL:
        ok = False
        print(f"  MISALIGNED: every pass-through net needs a dogleg "
              f"(tolerance {TOL} mm)")

    # 2. ... and the two should be mirrored about the board centreline.
    cx = board_centre_x(text)
    if cx is not None:
        d1 = cx - j1["1"][0][0]
        d2 = j2["1"][0][0] - cx
        print(f"pad columns from centre x={cx:.3f}: J1 {d1:.4f} mm, J2 {d2:.4f} mm")
        if abs(d1 - d2) > TOL:
            ok = False
            print(f"  NOT MIRRORED: differ by {abs(d1 - d2):.4f} mm")

    # 3. Board still matches the schematic, and report the DRC tally.
    rpt = HW / "drccheck.json"
    subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json",
                    "-o", str(rpt), str(PCB)], capture_output=True, text=True)
    drc = json.loads(rpt.read_text())
    rpt.unlink()
    parity = drc.get("schematic_parity", [])
    print(f"DRC: {len(drc.get('violations', []))} violation(s), "
          f"{len(drc.get('unconnected_items', []))} unconnected, "
          f"{len(parity)} schematic-parity issue(s)")
    for p in parity:
        ok = False
        print(f"  PARITY {p.get('type')}: {p.get('description', '')[:100]}")

    print("pcb:", "ok" if ok else "PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
