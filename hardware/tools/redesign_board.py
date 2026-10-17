# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Place the camera interposer for the supplied Raspberry Pi Camera v3 model.

Run with KiCad's Python from the repository root. The script updates pad nets
from the schematic, resets the existing copper, and creates the widened board
with a lens aperture. Run Freerouting afterward; no copper is pre-routed here.
"""

import math
import re
import subprocess
import tempfile
from pathlib import Path

import pcbnew

from kicad_cli import KICAD_CLI

HW = Path(__file__).resolve().parent.parent
PCB = HW / "rpi-camera-led.kicad_pcb"
SCH = HW / "rpi-camera-led.kicad_sch"

MM = pcbnew.FromMM


def point(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def export_schematic_nets():
    with tempfile.TemporaryDirectory() as temp_dir:
        netlist_path = Path(temp_dir) / "netlist.net"
        subprocess.run(
            [KICAD_CLI, "sch", "export", "netlist", "-o", netlist_path, SCH],
            check=True,
            capture_output=True,
            text=True,
        )
        text = netlist_path.read_text(encoding="utf-8")
    blocks = re.findall(
        r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\n\s*\(net\s+\(code|\Z)',
        text,
        re.DOTALL,
    )
    if not blocks:
        raise RuntimeError("KiCad exported no schematic nets")
    nets = {}
    for name, block in blocks:
        nodes = re.findall(
            r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)',
            block,
        )
        for ref, pin in nodes:
            if (ref, pin) in nets:
                raise RuntimeError(f"duplicate schematic pad {ref}.{pin}")
            nets[(ref, pin)] = name
    return nets


def add_net(board, name):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def add_outline(board):
    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(drawing)
    # 46 x 43 mm overall; 1.5 mm clipped corners keep the edge robust.
    corners = [
        (11.0, 14.5), (54.0, 14.5), (55.5, 16.0), (55.5, 56.0),
        (54.0, 57.5), (11.0, 57.5), (9.5, 56.0), (9.5, 19.0),
    ]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(point(*a))
        shape.SetEnd(point(*b))
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(MM(0.05))
        board.Add(shape)
    aperture = pcbnew.PCB_SHAPE(board)
    aperture.SetShape(pcbnew.SHAPE_T_CIRCLE)
    aperture.SetCenter(point(32.5, 31.931))
    aperture.SetEnd(point(38.0, 31.931))
    aperture.SetLayer(pcbnew.Edge_Cuts)
    aperture.SetWidth(MM(0.05))
    board.Add(aperture)


def add_lens_keepout(board):
    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    keepout.SetLayerSet(layers)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowZoneFills(True)
    outline = keepout.Outline()
    outline.NewOutline()
    for i in range(64):
        angle = 2 * math.pi * i / 64
        outline.Append(
            MM(32.5 + 6.05 * math.cos(angle)),
            MM(31.931 + 6.05 * math.sin(angle)),
        )
    board.Add(keepout)


def place(board):
    positions = {
        "J1": (13.0, 31.931, -90),
        "J2": (52.0, 31.931, 90),
        "J3": (17.5, 53.7, 180),
        "J4": (47.0, 49.0, 90),
        "U1": (32.5, 50.5, 180),
        "D1": (23.0, 25.5, 90),
        "D2": (42.0, 25.5, 90),
        "Q2": (32.5, 19.5, 90),
        "R3": (27.5, 25.5, 0),
        "R4": (37.5, 25.5, 0),
        "Q1": (41.0, 47.0, 0),
        "R5": (37.5, 47.0, 0),
        "R8": (41.0, 50.0, 0),
        "R9": (24.5, 46.5, 0),
        "R1": (37.5, 53.5, 90),
        "R2": (38.8, 53.5, 90),
        "R6": (32.5, 42.6, 0),
        "R7": (32.5, 43.87, 0),
        "C1": (23.5, 53.5, 0),
        "C2": (23.5, 55.5, 0),
    }
    for ref, (x, y, rotation) in positions.items():
        footprint = board.FindFootprintByReference(ref)
        if footprint is None:
            raise RuntimeError(f"missing footprint {ref}")
        footprint.SetPosition(point(x, y))
        footprint.SetOrientationDegrees(rotation)
    camera_holes = {
        "H1": (22.5, 19.431),
        "H2": (22.5, 31.931),
        "H3": (42.5, 19.431),
        "H4": (42.5, 31.931),
    }
    for ref, (x, y) in camera_holes.items():
        footprint = board.FindFootprintByReference(ref)
        if footprint is None:
            raise RuntimeError(f"missing camera mounting-hole footprint {ref}")
        footprint.SetPosition(point(x, y))
    board.FindFootprintByReference("R6").SetValue("10k")
    board.FindFootprintByReference("R7").SetValue("10k")
    board.FindFootprintByReference("R3").SetValue("47R")
    board.FindFootprintByReference("R4").SetValue("47R")
    reference_positions = {
        "D1": (23.0, 22.5),
        "R3": (27.5, 22.5),
        "Q2": (32.5, 16.5),
        "R4": (37.5, 22.5),
        "D2": (42.0, 22.5),
        "R7": (35.0, 42.7),
        "R8": (43.5, 50.0),
        "R1": (40.5, 52.0),
        "R2": (40.5, 55.0),
        "C1": (23.5, 52.0),
        "C2": (23.5, 56.5),
        "J3": (12.5, 53.7),
    }
    for ref, position in reference_positions.items():
        reference = board.FindFootprintByReference(ref).Reference()
        reference.SetPosition(point(*position))
    for footprint in board.GetFootprints():
        reference = footprint.Reference()
        reference.SetTextSize(point(0.8, 0.8))
        reference.SetTextThickness(MM(0.2))
        reference.SetTextAngleDegrees(0)


def update_nets(board, schematic_nets):
    footprints = {str(fp.GetReference()): fp for fp in board.GetFootprints()}
    for ref, footprint in footprints.items():
        for pad in footprint.Pads():
            net_name = schematic_nets.get((ref, str(pad.GetNumber())))
            if net_name:
                pad.SetNet(add_net(board, net_name))
            else:
                pad.SetNet(add_net(board, ""))


def main():
    board = pcbnew.LoadBoard(str(PCB))
    print("loaded board", flush=True)
    schematic_nets = export_schematic_nets()
    print("exported schematic nets", flush=True)
    place(board)
    print("placed footprints", flush=True)
    update_nets(board, schematic_nets)
    print("updated pad nets", flush=True)

    for item in list(board.GetTracks()):
        board.Delete(item)
    for zone in list(board.Zones()):
        board.Delete(zone)
    print("cleared old copper", flush=True)
    add_outline(board)
    print("updated outline", flush=True)
    add_lens_keepout(board)
    print("added lens copper keepout", flush=True)

    pcbnew.SaveBoard(str(PCB), board)
    print(f"Updated {PCB}")
    print("Board outline: 46 x 43 mm; lens aperture Ø11 mm; Raspberry Pi Camera v3 "
          "mounting holes at 20 x 12.5 mm.")
    print(f"Placement: {len(list(board.GetFootprints()))} footprints; "
          f"{len(list(board.GetTracks()))} tracks; route all nets after placement.")


if __name__ == "__main__":
    main()
