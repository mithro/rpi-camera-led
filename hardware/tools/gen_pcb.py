#!/usr/bin/env python3
"""Generate hardware/rpi-camera-led.kicad_pcb: outline, mounting holes, placement.

This script must run against the ``pcbnew`` Python module that ships inside the
KiCad 9 snap.  There is no interpreter inside ``/snap/kicad``, so the module is
reached by entering the snap's own runtime::

    echo 'python3 hardware/tools/gen_pcb.py' | snap run --shell kicad.pcbnew

(see hardware/tools/run_in_kicad.sh, which does exactly that).

Placement only -- track routing is done interactively in the pcbnew GUI and is
never rewritten by this script.  Re-running it regenerates the board from
scratch, so run it only when the placement itself needs to change.
"""

import os
import re
import sys

import pcbnew

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HW = os.path.join(REPO, "hardware")
PCB = os.path.join(HW, "rpi-camera-led.kicad_pcb")
NETLIST = os.path.join(REPO, "tmp", "netlist.net")
FPLIB = "/snap/kicad/current/usr/share/kicad/footprints"

# ----------------------------------------------------------------------------
# Board geometry.  Origin is arbitrary; the outline is a 25.0 x 24.0 mm
# rectangle, the same size as the Raspberry Pi Camera Module 2 PCB.
# ----------------------------------------------------------------------------
BX0, BY0 = 20.0, 20.0
BW, BH = 25.000, 23.862          # Raspberry Pi Camera Module 2 PCB outline
BX1, BY1 = BX0 + BW, BY0 + BH
CX, CY = BX0 + BW / 2.0, BY0 + BH / 2.0   # (32.5, 31.931)
CORNER_R = 2.0                   # "4x 2.0mm radius corners" (CM2 drawing)

# Camera Module 2 mounting pattern: 4 x "2.2mm diameter holes" on a
# 21.0 mm (X) x 12.5 mm (Y) grid.  On the camera the pattern is inset 2.0 mm
# from three edges (the fourth carries the FFC connector); this interposer has
# an FFC connector on *both* of the 23.862 mm edges, so the X inset of 2.0 mm
# is kept exactly while the pair of rows is centred between the two connectors
# -- at the camera's own Y offsets the holes would land on the connectors'
# solder tabs.  Spacing and diameter are unchanged.
MH_DX, MH_DY, MH_D = 21.0, 12.5, 2.2
MOUNT_HOLES = [
    (CX - MH_DX / 2, CY - MH_DY / 2),
    (CX + MH_DX / 2, CY - MH_DY / 2),
    (CX - MH_DX / 2, CY + MH_DY / 2),
    (CX + MH_DX / 2, CY + MH_DY / 2),
]

# ----------------------------------------------------------------------------
# Placement table: ref -> (x, y, rotation degrees)
#
# J1 sits on the left edge (cable out to the Raspberry Pi), J2 on the right
# edge (cable out to the camera); both housings are flush with the board edge
# and both openings point off the board.  Everything else lives in the 9.79 mm
# wide channel between the two connector courtyards (x 27.61 .. 37.40).
# ----------------------------------------------------------------------------
PLACE = {
    # FFC connectors: 22.0 x 5.3 mm housing, 15 contacts on 1.0 mm pitch.
    # Contact rows end up at x = 26.200 (J1) and x = 38.800 (J2).
    "J1": (22.825, 31.931, 270),
    "J2": (42.175, 31.931, 90),

    "J4": (29.40, 21.80, 90),      # SWD header (through hole) above the bus
    "U1": (32.50, 26.60, 0),       # CH32V003J4M6, SOIC-8
    "R6": (28.30, 24.70, 90),      # PI_IO0 <-> CAM_IO0 coupler
    "R7": (28.30, 27.20, 90),      # PI_IO1 <-> CAM_IO1 coupler
    "C1": (28.30, 29.60, 90),      # 100 nF, beside U1 VDD/VSS
    "R2": (36.75, 24.70, 90),      # SCL pull-up
    "R1": (36.75, 26.80, 90),      # SDA pull-up
    "C2": (36.75, 28.90, 90),      # 1 uF bulk
    "R5": (34.50, 30.00, 180),     # 100R, SWIO -> LED_GATE
    "Q1": (30.80, 31.40, 0),       # AO3400A low-side LED switch
    "R8": (34.50, 31.40, 0),       # LED_GATE pull-down
    "R9": (34.50, 32.80, 0),       # 47k phototransistor load
    "R3": (29.20, 34.10, 0),       # 10R to D1
    "R4": (35.00, 34.10, 0),       # 10R to D2
    "D1": (29.30, 36.20, 0),       # illumination LED (left)
    "D2": (35.00, 36.20, 0),       # illumination LED (right)
    "Q2": (32.15, 35.40, 90),      # phototransistor, between the two LEDs
    "J3": (32.50, 40.582, 0),      # Qwiic, opening flush with the bottom edge
}

FOOTPRINT_OVERRIDE = {}


def parse_netlist(path):
    """Return (components, nets) from a KiCad netlist s-expression."""
    text = open(path).read()
    comps = {}
    for m in re.finditer(
        r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)',
        text,
    ):
        comps[m.group(1)] = {"value": m.group(2), "footprint": m.group(3)}

    nets = {}
    net_block = text[text.index("(nets"):]
    for m in re.finditer(
        r'\(net \(code "\d+"\) \(name "([^"]+)"\)[^(]*(.*?)(?=\(net \(code|\Z)',
        net_block,
        re.S,
    ):
        name = m.group(1)
        pins = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2))
        nets[name] = pins
    return comps, nets


def _shape(board, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    return s


def add_edge_rect(board):
    """Rounded rectangle outline: 4 straight edges + 4 quarter-circle arcs."""
    r = CORNER_R
    segs = [
        ((BX0 + r, BY0), (BX1 - r, BY0)),
        ((BX1, BY0 + r), (BX1, BY1 - r)),
        ((BX1 - r, BY1), (BX0 + r, BY1)),
        ((BX0, BY1 - r), (BX0, BY0 + r)),
    ]
    for a, b in segs:
        s = _shape(board, pcbnew.Edge_Cuts)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I_MM(*a))
        s.SetEnd(pcbnew.VECTOR2I_MM(*b))
        board.Add(s)

    k = r * (1 - 2 ** -0.5)   # offset of the arc midpoint from the corner
    arcs = [
        ((BX0, BY0 + r), (BX0 + k, BY0 + k), (BX0 + r, BY0)),
        ((BX1 - r, BY0), (BX1 - k, BY0 + k), (BX1, BY0 + r)),
        ((BX1, BY1 - r), (BX1 - k, BY1 - k), (BX1 - r, BY1)),
        ((BX0 + r, BY1), (BX0 + k, BY1 - k), (BX0, BY1 - r)),
    ]
    for a, m, b in arcs:
        s = _shape(board, pcbnew.Edge_Cuts)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(pcbnew.VECTOR2I_MM(*a),
                         pcbnew.VECTOR2I_MM(*m),
                         pcbnew.VECTOR2I_MM(*b))
        board.Add(s)


def add_mounting_holes(board):
    """Plain NPTH holes.

    The stock MountingHole_2.2mm_M2 footprint carries a 4.9 mm diameter
    courtyard which would collide with the FFC connector courtyards, so the
    hole is built here with copper/keepout geometry only.
    """
    for i, (x, y) in enumerate(MOUNT_HOLES, start=1):
        fp = pcbnew.FOOTPRINT(board)
        fp.SetFPID(pcbnew.LIB_ID("local", "MountingHole_2.2mm_M2_NoCourtyard"))
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetReference("H%d" % i)
        fp.SetValue("MountingHole_2.2mm")
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(pcbnew.FP_THROUGH_HOLE | pcbnew.FP_EXCLUDE_FROM_BOM)

        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I_MM(MH_D, MH_D))
        pad.SetDrillSize(pcbnew.VECTOR2I_MM(MH_D, MH_D))
        pad.SetLayerSet(pad.UnplatedHoleMask())
        pad.SetNumber("")
        pad.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.Add(pad)

        circ = pcbnew.PCB_SHAPE(fp)
        circ.SetShape(pcbnew.SHAPE_T_CIRCLE)
        circ.SetCenter(pcbnew.VECTOR2I_MM(x, y))
        circ.SetEnd(pcbnew.VECTOR2I_MM(x + MH_D / 2 + 0.25, y))
        circ.SetLayer(pcbnew.F_SilkS)
        circ.SetWidth(pcbnew.FromMM(0.12))
        fp.Add(circ)

        board.Add(fp)


def add_zone(board, layer, netcode, priority):
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNetCode(netcode)
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(pcbnew.FromMM(0.2))
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    outline = zone.Outline()
    outline.NewOutline()
    import math
    inset = 0.15
    r = CORNER_R - inset
    for cx, cy, a0 in ((BX0 + CORNER_R, BY0 + CORNER_R, 180.0),
                       (BX1 - CORNER_R, BY0 + CORNER_R, 270.0),
                       (BX1 - CORNER_R, BY1 - CORNER_R, 0.0),
                       (BX0 + CORNER_R, BY1 - CORNER_R, 90.0)):
        for i in range(9):
            a = math.radians(a0 + i * 90.0 / 8.0)
            outline.Append(pcbnew.FromMM(cx + r * math.cos(a)),
                           pcbnew.FromMM(cy + r * math.sin(a)))
    zone.SetIsFilled(False)
    board.Add(zone)
    return zone


def main():
    comps, nets = parse_netlist(NETLIST)

    board = pcbnew.CreateEmptyBoard()

    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.SetBoardThickness(pcbnew.FromMM(1.6))

    # Net classes / default rules.
    netsettings = board.GetAllNetClasses()
    default = netsettings["Default"]
    default.SetClearance(pcbnew.FromMM(0.15))
    default.SetTrackWidth(pcbnew.FromMM(0.2))
    default.SetViaDiameter(pcbnew.FromMM(0.6))
    default.SetViaDrill(pcbnew.FromMM(0.3))

    add_edge_rect(board)
    add_mounting_holes(board)

    # Nets -------------------------------------------------------------------
    netmap = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni

    # Footprints -------------------------------------------------------------
    missing = []
    for ref in sorted(comps):
        if ref not in PLACE:
            missing.append(ref)
            continue
        fpid = FOOTPRINT_OVERRIDE.get(ref, comps[ref]["footprint"])
        lib, name = fpid.split(":", 1)
        fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)
        if fp is None:
            raise SystemExit("could not load footprint %s" % fpid)
        board.Add(fp)
        x, y, rot = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetOrientationDegrees(rot)
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"])
        # Keep silkscreen text small and out of the way on this dense board.
        for txt in (fp.Reference(), fp.Value()):
            txt.SetTextSize(pcbnew.VECTOR2I_MM(0.5, 0.5))
            txt.SetTextThickness(pcbnew.FromMM(0.08))
        fp.Value().SetVisible(False)
    if missing:
        raise SystemExit("no placement for: %s" % ", ".join(missing))

    # Pad -> net -------------------------------------------------------------
    assigned = 0
    for netname, pins in nets.items():
        ni = netmap[netname]
        for ref, pin in pins:
            fp = board.FindFootprintByReference(ref)
            pad = fp.FindPadByNumber(pin)
            if pad is None:
                raise SystemExit("pad %s.%s not found" % (ref, pin))
            pad.SetNet(ni)
            assigned += 1

    gnd = netmap["GND"]
    add_zone(board, pcbnew.B_Cu, gnd.GetNetCode(), 10)
    add_zone(board, pcbnew.F_Cu, gnd.GetNetCode(), 10)

    board.BuildListOfNets()
    pcbnew.SaveBoard(PCB, board)
    print("wrote %s" % PCB)
    print("footprints=%d nets=%d pad-net assignments=%d"
          % (len(board.GetFootprints()), len(nets), assigned))

    # Report key pad coordinates so the routing plan can be checked.
    for ref in ("J1", "J2"):
        fp = board.FindFootprintByReference(ref)
        pads = []
        for pad in fp.Pads():
            if pad.GetNumber() in ("1", "8", "15"):
                p = pad.GetPosition()
                pads.append("%s=(%.3f,%.3f)"
                            % (pad.GetNumber(), pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))
        print("%s pads: %s" % (ref, "  ".join(sorted(pads))))


if __name__ == "__main__":
    sys.exit(main())
