# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Verify FFC alignment, J3 placement, and the Raspberry Pi Camera v3 hole pattern.

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
from kicad_cli import KICAD_CLI

TOL = 0.001  # mm; anything above this is a real misalignment, not rounding

# Hole coordinates are read from the project-local Raspberry Pi Camera v3 3MF
# model relative to its lens axis, then mapped to the interposer aperture.
MH_DX, MH_DY, MH_DRILL = 20.0, 12.5, 2.2
CAMERA_HOLES = {
    (22.5, 19.431),
    (22.5, 31.931),
    (42.5, 19.431),
    (42.5, 31.931),
}


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


def mounting_holes(text):
    """[(reference, x, y, drill diameter), ...] for the NPTH mounting holes."""
    out = []
    for m in re.finditer(r'\(footprint "([^"]+)"', text):
        block = text[m.start():sexp_end(text, m.start())]
        if "MountingHole" not in m.group(1):
            continue
        ref = re.search(r'\(property "Reference" "([^"]*)"', block)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", block)
        drill = re.search(r"\(drill ([-\d.]+)\)", block)
        if ref and at:
            out.append((ref.group(1), float(at.group(1)), float(at.group(2)),
                        float(drill.group(1)) if drill else None))
    return out


def footprint_locations(text):
    """reference -> (x, y, angle) in board coordinates."""
    out = {}
    for m in re.finditer(r'\(footprint "([^"]+)"', text):
        block = text[m.start():sexp_end(text, m.start())]
        ref = re.search(r'\(property "Reference" "([^"]*)"', block)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", block)
        if ref and at:
            out[ref.group(1)] = (
                float(at.group(1)),
                float(at.group(2)),
                float(at.group(3) or 0),
            )
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

    # 3. The Qwiic cable entry faces outward at the lower board edge.
    loc = footprint_locations(text).get("J3")
    expected_loc = (17.5, 53.7, 180.0)
    if loc is None:
        ok = False
        print("Qwiic connector J3 is missing")
    else:
        error = max(abs(a - b) for a, b in zip(loc, expected_loc))
        print(f"Qwiic J3 placement: {loc[0]:.3f}, {loc[1]:.3f} mm at {loc[2]:.1f}°")
        if error > TOL:
            ok = False
            print("  WRONG EDGE ORIENTATION: expected (17.5, 53.7) mm at 180°")
        expected_pads = {
            "1": (19.0, 51.7),
            "2": (18.0, 51.7),
            "3": (17.0, 51.7),
            "4": (16.0, 51.7),
        }
        for number, expected in expected_pads.items():
            actual = fps.get("J3", {}).get(number, [])
            if len(actual) != 1 or max(abs(a - b) for a, b in zip(actual[0], expected)) > TOL:
                ok = False
                print(f"  WRONG J3.{number} pad position: expected {expected}, found {actual}")

    # 4. The mounting pattern must match the supplied camera model at the
    #    actual aperture datum, not the previous Camera Module 2 assumption.
    holes = mounting_holes(text)
    print(f"mounting holes: {len(holes)}")
    if len(holes) != 4:
        ok = False
        print("  EXPECTED 4 (the Raspberry Pi Camera v3 pattern)")
    else:
        xs = sorted({round(h[1], 3) for h in holes})
        ys = sorted({round(h[2], 3) for h in holes})
        drills = {h[3] for h in holes}
        if len(xs) == 2 and len(ys) == 2:
            dx, dy = xs[1] - xs[0], ys[1] - ys[0]
            print(f"  pitch {dx:.3f} x {dy:.3f} mm, drill {sorted(drills)} mm")
            actual_positions = {
                (round(h[1], 3), round(h[2], 3)) for h in holes
            }
            if abs(dx - MH_DX) > TOL or abs(dy - MH_DY) > TOL:
                ok = False
                print(f"  WRONG PITCH: expected {MH_DX} x {MH_DY} mm")
            if actual_positions != CAMERA_HOLES:
                ok = False
                print(f"  WRONG CAMERA DATUM: expected {sorted(CAMERA_HOLES)}, "
                      f"found {sorted(actual_positions)}")
        else:
            ok = False
            print(f"  NOT A RECTANGULAR PATTERN: x={xs} y={ys}")
        if drills != {MH_DRILL}:
            ok = False
            print(f"  WRONG DRILL: expected {MH_DRILL} mm, found {sorted(drills)}")

    # 5. Board still matches the schematic, and report the DRC tally.
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
