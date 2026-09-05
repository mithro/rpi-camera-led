#!/usr/bin/env python3
"""Put the Raspberry Pi camera board's mounting holes on the interposer.

The interposer uses the Camera Module 2 outline, so it should take the same
screws.  From the official mechanical drawing (RP-008149-DS, RPI-CAM-V2_1):

    "4x 2.2mm diameter holes"
    "4x 2.0mm radius corners"
    25.000 x 23.862 mm board

with the holes 2 mm in from each end of the 25 mm axis -- a 21.0 mm pitch --
and at 2.0 and 14.5 mm from one end of the 23.862 mm axis, a 12.5 mm pitch.
That second pair is asymmetric on the camera because its FFC connector eats
the far edge; here the pair is centred instead, which is what this board
carried before the holes were lost.

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

BX0, BY0, BW, BH = 20.0, 20.0, 25.000, 23.862
CX, CY = BX0 + BW / 2.0, BY0 + BH / 2.0
MH_DX, MH_DY = 21.0, 12.5          # camera pitches, 25mm axis x 23.862mm axis

HOLES = [(CX + sx * MH_DX / 2.0, CY + sy * MH_DY / 2.0)
         for sx in (-1, 1) for sy in (-1, 1)]


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
