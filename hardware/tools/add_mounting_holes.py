#!/usr/bin/env python3
"""Put the supplied Raspberry Pi Camera v3 model's mounting holes on the interposer.

Runs inside the KiCad snap, for the pcbnew module:
    hardware/tools/run_in_kicad.sh python3 hardware/tools/add_mounting_holes.py

The stock MountingHole_2.2mm_M2 footprint is used deliberately, courtyard and
all.  An earlier version of this board hand-built the holes without one
precisely so they would not trip DRC against the FFC connectors -- which
silenced a real mechanical conflict rather than reporting it.
"""

import os
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "rpi-camera-led.kicad_pcb")

LIB = "/snap/kicad/current/usr/share/kicad/footprints/MountingHole.pretty"
FP = "MountingHole_2.2mm_M2"

# The project-local 3MF places the optical axis at its XY origin and the
# mounting holes at (+/-10, 0) and (+/-10, 12.5) mm. The assembly is rotated
# 180 degrees and centered on the interposer's 32.5, 31.931 mm aperture.
APERTURE_X, APERTURE_Y = 32.5, 31.931
MH_DX, MH_DY = 20.0, 12.5
HOLES = [
    (APERTURE_X + sx * MH_DX / 2.0, APERTURE_Y + dy)
    for sx in (-1, 1)
    for dy in (0.0, -MH_DY)
]


def main():
    board = pcbnew.LoadBoard(PCB)

    # Idempotent: drop any hole we previously added before adding them again.
    for fp in list(board.GetFootprints()):
        if fp.GetReference().startswith("H") and "MountingHole" in str(fp.GetFPIDAsString()):
            board.Remove(fp)

    for i, (x, y) in enumerate(sorted(HOLES), start=1):
        fp = pcbnew.FootprintLoad(LIB, FP)
        if fp is None:
            print(f"could not load {FP} from {LIB}", file=sys.stderr)
            return 1
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetReference("H%d" % i)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
        print(f"H{i}  ({x:6.3f}, {y:6.3f})")

    pcbnew.SaveBoard(PCB, board)
    print(f"\n{len(HOLES)} holes, {MH_DX} x {MH_DY} mm, 2.2mm dia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
