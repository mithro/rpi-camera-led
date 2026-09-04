# /// script
# requires-python = ">=3.11"
# dependencies = ["cadquery>=2.8"]
# ///
"""Build 3D models for the JUSHUO AFA07-S15 FFC connectors.

KiCad's stock footprints reference
``Connector_FFC-FPC.3dshapes/JUSHUO_AFA07-S15FCA-00_...step``, but no such
file exists -- not in the snap, and not in kicad-packages3D upstream, which
ships no JUSHUO models at all.  Third-party libraries have them, but under
terms that do not permit redistribution, so this builds one from the
manufacturer's published drawing instead, which an Apache-2.0 repository can
actually carry.

Geometry, all from the JUSHUO AFA07-S series drawing (LCSC doc 2304140030)
and KiCad's stock footprint, whose F.Fab outline is the manufacturer's body
outline and whose land pattern was verified against that drawing pad for pad:

    housing plan outline   F.Fab, front face at y=-2.475, back at y=+2.825
                           (5.30mm deep, matching the drawing's "5.30")
                           20.05mm across the front  = drawing DIM C
                           22.00mm across the ears   = drawing DIM D
    slide lock plan        F.Fab, y=+2.825 to +4.475, drawn open
    height                 2.50mm, the side view's "2.50" and the "H2.5" in
                           the product name "1.0Pitch H2.5 FPC ZIF R/A"
    contact tails          on the land pattern: 15 x 0.6mm at 1.00mm pitch
    colours                drawing note 1.1 "Housing: ... Color: natural",
                           note 1.2 "Latch: ... Color: black"

The cable enters at the LATCH end, not the terminal end.  Section A-A shows
the solder tail stepping down and out one side while the cable channel opens
the other, and the top view labels "Terminal" at one end and "Latch" at the
other with the 5.30mm housing between them -- which is also how a slide lock
has to work, since you pull the slider, insert the cable and push it back at
the same end.  So the slot is cut from y=+4.475 inwards.

Its height is the one invented dimension; the drawing does not give it.  The
slot only eats into the latch end and does not change the outside envelope,
which is what a clearance check needs.

The two variants differ only in which side of the slot the contacts are on,
which is internal, so both get the same body -- written out twice under the
two names so each footprint can reference a correctly named file.

Usage (from the repository root):
    uv run hardware/tools/gen_connector_model.py
"""

import sys
from pathlib import Path

import cadquery as cq

HW = Path(__file__).resolve().parent.parent
OUT = HW / "rpi-camera-led.3dshapes"

NAMES = [
    "JUSHUO_AFA07-S15FCA-00_1x15-1MP_P1.0mm_Horizontal",
    "JUSHUO_AFA07-S15ECA-00_1x15-1MP_P1.0mm_Horizontal",
]

HEIGHT = 2.50       # side view "2.50", and the H2.5 in the product name
LATCH_TOP = 2.00    # the lock sits proud of the board but below the housing
SLOT_Z = (0.60, 0.95)   # representative; the drawing does not dimension it
SLOT_HALF_W = 8.20      # a little wider than the 16.00mm cable
SLOT_DEPTH = 4.15       # from the latch face at y=+4.475, through into the body

# FFC cable stub, for the illustrative render only.  Width and thickness are
# the drawing's RECOMMENDED FPC/FFC DIMENSION: (N+1) x 1.00 = 16.00 for 15
# ways, 0.30 +/- 0.03 thick.  The length is arbitrary -- just enough to run
# clear of the board.
CABLE_W, CABLE_T, CABLE_LEN = 16.00, 0.30, 22.0
INSERT = 4.00        # how far the tip sits inside the connector
EXPOSED = 6.00       # bared conductors at the tip, so ~2mm shows outside
STIFF_LEN = 9.00     # blue backing, so ~5mm shows outside
STIFF_T = 0.15
COND_W, COND_T = 0.70, 0.04   # one bared conductor, on the pitch of the pads

# Plan outlines, in KiCad *footprint* coordinates, taken from the F.Fab layer
# of Connector_FFC-FPC:JUSHUO_AFA07-S15FCA-00_1x15-1MP_P1.0mm_Horizontal.
HOUSING = [
    (-10.025, -2.475), (10.025, -2.475), (10.025, -0.675), (10.650, -0.675),
    (10.650, 0.325), (11.000, 1.825), (11.000, 2.825), (-11.000, 2.825),
    (-11.000, 1.825), (-10.650, 0.325), (-10.650, -0.675), (-10.025, -0.675),
]
LATCH = [
    (-11.000, 3.475), (-10.025, 3.475), (-10.025, 2.825), (10.025, 2.825),
    (10.025, 3.475), (11.000, 3.475), (11.000, 4.475), (-11.000, 4.475),
]

# Contact tails, sitting on the land pattern: pad 1 at x=-7, 1.00mm pitch,
# pads 0.6 x 1.8 centred at y=-3.375.
CONTACT_W, CONTACT_D, CONTACT_H = 0.60, 1.80, 0.15
CONTACT_Y = -3.375

# Drawing note 1: housing natural thermoplastic, latch black.  Tin plating
# per note 2.1 ("Underplating: Au/matt Tin overall").
COLOURS = {
    "housing": (0.85, 0.82, 0.72),
    "latch": (0.13, 0.13, 0.14),
    "contacts": (0.75, 0.76, 0.78),
    "cable": (0.93, 0.91, 0.84),
    "stiffener": (0.16, 0.29, 0.55),
    "conductors": (0.80, 0.66, 0.40),
}

VRML_SCALE = 2.54  # KiCad reads .wrl in 0.1 inch units; .step is plain mm


def to_model(pts):
    """Footprint coordinates -> KiCad 3D model coordinates (Y is negated)."""
    return [(x, -y) for x, y in pts]


def build():
    housing = (cq.Workplane("XY").polyline(to_model(HOUSING)).close()
               .extrude(HEIGHT))
    latch = (cq.Workplane("XY").polyline(to_model(LATCH)).close()
             .extrude(LATCH_TOP))

    # Cable slot, cut in from the latch face (model y = -4.475) towards the
    # terminals.  It passes through the latch and on into the housing, so both
    # solids have to be cut.
    slot = (cq.Workplane("XY")
            .box(2 * SLOT_HALF_W, SLOT_DEPTH, SLOT_Z[1] - SLOT_Z[0],
                 centered=(True, False, False))
            .translate((0, -4.475, SLOT_Z[0])))
    housing = housing.cut(slot)
    latch = latch.cut(slot)

    contacts = None
    for i in range(15):
        x = -7.0 + i
        c = (cq.Workplane("XY")
             .box(CONTACT_W, CONTACT_D, CONTACT_H, centered=(True, True, False))
             .translate((x, -CONTACT_Y, 0)))
        contacts = c if contacts is None else contacts.union(c)

    return {"housing": housing, "latch": latch, "contacts": contacts}


def build_cable(contacts_down):
    """An FFC cable stub, entering the slot and running away from the board.

    Illustrative only -- it is not part of the connector, and only goes into
    the _with_cable models that the README renders use.

    The two faces are not interchangeable, which is the whole point of pairing
    a bottom-contact J1 with a top-contact J2, so the stub is built both ways
    round: the bared conductors go on the face the connector's contacts are
    on, and the blue backing goes on the other.  Both are at the same end, and
    both are drawn long enough that a few millimetres stay visible outside the
    connector -- otherwise the orientation they exist to show would be hidden
    inside it.
    """
    z = SLOT_Z[0]
    tip = -4.475 + INSERT          # model y; the cable runs out towards -y
    body = (cq.Workplane("XY")
            .box(CABLE_W, CABLE_LEN + INSERT, CABLE_T, centered=(True, False, False))
            .translate((0, tip - (CABLE_LEN + INSERT), z)))

    if contacts_down:
        cond_z, stiff_z = z - COND_T, z + CABLE_T
    else:
        cond_z, stiff_z = z + CABLE_T, z - STIFF_T

    conductors = None
    for i in range(15):
        c = (cq.Workplane("XY")
             .box(COND_W, EXPOSED, COND_T, centered=(True, False, False))
             .translate((-7.0 + i, tip - EXPOSED, cond_z)))
        conductors = c if conductors is None else conductors.union(c)

    stiffener = (cq.Workplane("XY")
                 .box(CABLE_W, STIFF_LEN, STIFF_T, centered=(True, False, False))
                 .translate((0, tip - STIFF_LEN, stiff_z)))

    return {"cable": body, "stiffener": stiffener, "conductors": conductors}


def write_vrml(path, parts):
    """Tessellate each solid and emit one coloured VRML Shape per part."""
    out = ["#VRML V2.0 utf8",
           "# JUSHUO AFA07-S15 FFC connector, built from the manufacturer's",
           "# drawing by hardware/tools/gen_connector_model.py",
           "Transform {", "  children ["]
    for name, wp in parts.items():
        verts, tris = wp.val().tessellate(0.01)
        r, g, b = COLOURS[name]
        coords = ", ".join(
            f"{v.x / VRML_SCALE:.6f} {v.y / VRML_SCALE:.6f} {v.z / VRML_SCALE:.6f}"
            for v in verts)
        index = ", ".join(f"{a} {b_} {c} -1" for a, b_, c in tris)
        out += [
            "    Shape {",
            "      appearance Appearance { material Material {",
            f"        diffuseColor {r:.3f} {g:.3f} {b:.3f}",
            f"        specularColor 0.15 0.15 0.15  shininess 0.3",
            "      } }",
            "      geometry IndexedFaceSet {",
            "        solid TRUE",
            f"        coord Coordinate {{ point [ {coords} ] }}",
            f"        coordIndex [ {index} ]",
            "      }", "    }",
        ]
    out += ["  ]", "}", ""]
    path.write_text("\n".join(out))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parts = build()

    asm = cq.Assembly()
    for name, wp in parts.items():
        asm.add(wp, name=name, color=cq.Color(*COLOURS[name]))

    # The cable variant is WRL only: it exists to make a render legible, and a
    # cable stub is not something anyone wants in an MCAD assembly.  F is the
    # lower-contact part, so its cable presents copper downwards; E is upper,
    # so its cable is the other way up.
    for name in NAMES:
        with_cable = dict(parts)
        with_cable.update(build_cable(contacts_down="FCA" in name))
        step = OUT / f"{name}.step"
        wrl = OUT / f"{name}.wrl"
        cable_wrl = OUT / f"{name}_with_cable.wrl"
        asm.save(str(step))
        write_vrml(wrl, parts)
        write_vrml(cable_wrl, with_cable)
        for f in (step, wrl, cable_wrl):
            print(f"{f.relative_to(HW.parent)}  ({f.stat().st_size // 1024} KiB)")

    bb = parts["housing"].union(parts["latch"]).val().BoundingBox()
    print(f"\nenvelope  X {bb.xmin:+.3f}..{bb.xmax:+.3f}  "
          f"Y {bb.ymin:+.3f}..{bb.ymax:+.3f}  Z {bb.zmin:+.3f}..{bb.zmax:+.3f} mm")
    print(f"          {bb.xlen:.2f} wide x {bb.ylen:.2f} deep x {bb.zlen:.2f} tall")


if __name__ == "__main__":
    sys.exit(main())
