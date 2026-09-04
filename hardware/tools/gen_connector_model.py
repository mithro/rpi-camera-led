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

The cable slot is the one invented feature: the drawing does not dimension
it, so its height is representative.  It only cuts into the front face and
does not change the outside envelope, which is what a clearance check needs.

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
SLOT_Z = (0.60, 1.20)   # representative; the drawing does not dimension it
SLOT_HALF_W = 7.70      # just wider than the 15 contacts, which span +/-7.0
SLOT_DEPTH = 4.00       # into the housing from the front face

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
}

VRML_SCALE = 2.54  # KiCad reads .wrl in 0.1 inch units; .step is plain mm


def to_model(pts):
    """Footprint coordinates -> KiCad 3D model coordinates (Y is negated)."""
    return [(x, -y) for x, y in pts]


def build():
    housing = (cq.Workplane("XY").polyline(to_model(HOUSING)).close()
               .extrude(HEIGHT))
    # Cable slot, cut back from the front face (which is at model y=+2.475).
    slot = (cq.Workplane("XY")
            .box(2 * SLOT_HALF_W, SLOT_DEPTH, SLOT_Z[1] - SLOT_Z[0],
                 centered=(True, False, False))
            .translate((0, 2.475 - SLOT_DEPTH, SLOT_Z[0])))
    housing = housing.cut(slot)

    latch = (cq.Workplane("XY").polyline(to_model(LATCH)).close()
             .extrude(LATCH_TOP))

    contacts = None
    for i in range(15):
        x = -7.0 + i
        c = (cq.Workplane("XY")
             .box(CONTACT_W, CONTACT_D, CONTACT_H, centered=(True, True, False))
             .translate((x, -CONTACT_Y, 0)))
        contacts = c if contacts is None else contacts.union(c)

    return {"housing": housing, "latch": latch, "contacts": contacts}


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

    for name in NAMES:
        step = OUT / f"{name}.step"
        wrl = OUT / f"{name}.wrl"
        asm.save(str(step))
        write_vrml(wrl, parts)
        print(f"{step.relative_to(HW.parent)}  ({step.stat().st_size // 1024} KiB)")
        print(f"{wrl.relative_to(HW.parent)}  ({wrl.stat().st_size // 1024} KiB)")

    bb = parts["housing"].union(parts["latch"]).val().BoundingBox()
    print(f"\nenvelope  X {bb.xmin:+.3f}..{bb.xmax:+.3f}  "
          f"Y {bb.ymin:+.3f}..{bb.ymax:+.3f}  Z {bb.zmin:+.3f}..{bb.zmax:+.3f} mm")
    print(f"          {bb.xlen:.2f} wide x {bb.ylen:.2f} deep x {bb.zlen:.2f} tall")


if __name__ == "__main__":
    sys.exit(main())
