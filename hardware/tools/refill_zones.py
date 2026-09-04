#!/usr/bin/env python3
"""Refill the copper zones in hardware/rpi-camera-led.kicad_pcb.

kicad-cli has no zone-fill command, so this runs inside the KiCad snap where
the pcbnew Python module lives, and calls the same ZONE_FILLER that the GUI's
Edit > Fill All Zones (the "B" key) invokes.  Nothing here is a design
decision -- it just brings the stored fills back in step with the copper, so a
render or a plot shows the pours as they would actually be manufactured.

Usage (from the repository root):
    hardware/tools/run_in_kicad.sh python3 hardware/tools/refill_zones.py

Prints the fill area per zone before and after, so a stale pour is visible
rather than silently corrected.
"""

import os
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "rpi-camera-led.kicad_pcb")


def areas(board):
    """(net, layer, filled area in mm^2) for every zone."""
    out = []
    for z in board.Zones():
        a = 0.0
        for layer in z.GetLayerSet().Seq():
            poly = z.GetFilledPolysList(layer)
            if poly:
                a += poly.Area() / 1e12  # internal units are nm
        out.append((z.GetNetname(), board.GetLayerName(z.GetFirstLayer()), a))
    return out


def main():
    board = pcbnew.LoadBoard(PCB)
    before = areas(board)

    filler = pcbnew.ZONE_FILLER(board)
    ok = filler.Fill(board.Zones())
    if not ok:
        print("ZONE_FILLER.Fill() reported failure", file=sys.stderr)
        return 1

    after = areas(board)
    for (net, layer, a0), (_, _, a1) in zip(before, after):
        delta = a1 - a0
        note = "  unchanged" if abs(delta) < 1e-6 else f"  {delta:+.3f} mm^2"
        print(f"{layer:6s} {net:8s}  {a0:8.3f} -> {a1:8.3f} mm^2{note}")

    pcbnew.SaveBoard(PCB, board)
    print(f"\nsaved {os.path.relpath(PCB, os.path.dirname(HW))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
