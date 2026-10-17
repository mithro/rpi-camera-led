# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Add and refill the camera interposer's B.Cu ground plane.

Run with KiCad's Python from the repository root after routing.
"""

from pathlib import Path

import pcbnew

PCB = Path(__file__).resolve().parent.parent / "rpi-camera-led.kicad_pcb"
MM = pcbnew.FromMM


def main():
    board = pcbnew.LoadBoard(str(PCB))
    if any(z.GetLayer() == pcbnew.B_Cu and z.GetNetname() == "GND"
           for z in board.Zones()):
        raise RuntimeError("a B.Cu GND plane already exists")
    ground = board.FindNet("GND")
    if ground is None:
        raise RuntimeError("GND net is missing from the board")

    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetNetCode(ground.GetNetCode())
    zone.SetLocalClearance(MM(0.2))
    zone.SetThermalReliefGap(MM(0.25))
    zone.SetThermalReliefSpokeWidth(MM(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetZoneName("B.Cu_GND")
    outline = [
        (10.0, 15.0), (55.0, 15.0), (55.0, 57.0), (10.0, 57.0),
    ]
    zone.Outline().NewOutline()
    for x, y in outline:
        zone.Outline().Append(MM(x), MM(y))
    board.Add(zone)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)
    print(f"Added/refilled B.Cu GND zone in {PCB}")


if __name__ == "__main__":
    main()
