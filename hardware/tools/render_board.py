# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Regenerate the board images that README.md embeds.

Writes into docs/img/:

    board-3d-top.png     raytraced 3D render, viewed from the front
    board-3d-bottom.png  the same from the back
    board-layout.svg     F.Cu / B.Cu / F.SilkS / Edge.Cuts, board area only
    board-3d-cables.png  top view with FFC cable stubs in both connectors
    board-3d-iso.png     isometric view, also with the cables

The zone fills are refilled first.  kicad-cli cannot do that, so it shells out
to the pcbnew Python module inside the KiCad snap; skip it with --no-refill.
Rendering a stale pour is worse than not rendering at all, because it looks
authoritative -- when this was first written the stored B.Cu pour was less
than half its true area.

The 3D views are deliberately zoomed out far enough to include every
footprint, not just the ones inside the board outline -- eleven parts are
still sitting off the board while the layout is in progress, and cropping
them out of the README would make the board look more finished than it is.

Usage (from the repository root):
    uv run hardware/tools/render_board.py [--no-refill]
"""

import re
import subprocess
import sys
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
PCB = HW / "rpi-camera-led.kicad_pcb"
IMG = HW.parent / "docs" / "img"
TMP = HW.parent / "tmp"
SHAPES = HW / "rpi-camera-led.3dshapes"

KICAD_CLI = "/snap/bin/kicad.kicad-cli"
# kicad-cli does not inherit the GUI's path substitutions, so the models
# resolve to nothing unless this is handed to it explicitly.
MODEL_DIR = "/snap/kicad/current/usr/share/kicad/3dmodels"

# The three README panels sit side by side, so they are given a common aspect
# ratio: the SVG's page is whatever KiCad's "board area only" mode computes,
# and the 3D renders are widened to match it.  Deriving the width instead of
# hardcoding it keeps them matched if the board outline changes.
HEIGHT = 1500
ZOOM = "0.45"  # fits the off-board footprints too; see the note above
LAYERS = "F.Cu,B.Cu,F.SilkS,Edge.Cuts"

# The cable stubs run 22mm out of each connector, so these views have to pull
# back a lot further and are much wider than they are tall.
CABLE_SIZE, CABLE_ZOOM = (1800, 1000), "0.46"
# 315 rather than -45: kicad-cli's parser reads a leading "-" as a new flag.
ISO_SIZE, ISO_ZOOM, ISO_ROTATE = (1600, 1100), "0.42", "315,0,45"


def run(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"failed: {' '.join(map(str, args))}")
    return r


def refill_zones():
    """Bring the stored copper pours back in step with the board."""
    r = subprocess.run([str(HW / "tools" / "run_in_kicad.sh"), "python3",
                        str(HW / "tools" / "refill_zones.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("could not refill zones (rendering the stored fill instead):",
              file=sys.stderr)
        print(r.stderr.strip()[:400], file=sys.stderr)
        return
    for line in r.stdout.strip().splitlines():
        print(f"  {line}")


def render(out, extra, size, zoom, board):
    w, h = size
    r = run([KICAD_CLI, "pcb", "render", "-o", str(out),
             "--width", str(w), "--height", str(h), "--quality", "high",
             "--background", "opaque", "--zoom", zoom,
             "-D", f"KICAD9_3DMODEL_DIR={MODEL_DIR}", *extra, str(board)])
    print(f"{out.relative_to(HW.parent)}  "
          f"({out.stat().st_size // 1024} KiB, {w} x {h} px)")
    return r


def board_with_cables():
    """A throwaway copy of the board whose connectors carry a cable stub.

    The cable is illustrative, so it must not end up in the real board.  The
    copy uses absolute model paths because ${KIPRJMOD} would otherwise resolve
    to the copy's own directory.
    """
    TMP.mkdir(exist_ok=True)
    out = TMP / "board-with-cables.kicad_pcb"
    t = PCB.read_text()
    n = 0
    for m in set(re.findall(r'\$\{KIPRJMOD\}/rpi-camera-led\.3dshapes/([^"]+)\.step', t)):
        t = t.replace(f"${{KIPRJMOD}}/rpi-camera-led.3dshapes/{m}.step",
                      str(SHAPES / f"{m}_with_cable.wrl"))
        n += 1
    assert n == 2, f"expected 2 connector models to swap, swapped {n}"
    out.write_text(t)
    return out


def main():
    if "--no-refill" not in sys.argv:
        print("refilling zones:")
        refill_zones()
    IMG.mkdir(parents=True, exist_ok=True)

    # The SVG goes first: its page sets the aspect ratio the renders copy.
    svg = IMG / "board-layout.svg"
    run([KICAD_CLI, "pcb", "export", "svg", "-o", str(svg),
         "--layers", LAYERS, "--mode-single", "--page-size-mode", "2",
         "--exclude-drawing-sheet", "--drill-shape-opt", "2", str(PCB)])
    head = svg.read_text()[:2000]
    w = float(re.search(r'width="([\d.]+)mm"', head).group(1))
    h = float(re.search(r'height="([\d.]+)mm"', head).group(1))
    width = round(HEIGHT * w / h)
    print(f"{svg.relative_to(HW.parent)}  ({svg.stat().st_size // 1024} KiB, "
          f"{w:.2f} x {h:.2f} mm, aspect {w / h:.4f})")

    missing = set()
    for side in ("top", "bottom"):
        r = render(IMG / f"board-3d-{side}.png", ["--side", side],
                   (width, HEIGHT), ZOOM, PCB)
        # KiCad reports a miss on stderr, as a wxWidgets trace line.
        for line in (r.stdout + r.stderr).splitlines():
            if "could not find model" in line:
                missing.add(line.split("'")[1] if "'" in line else line.strip())

    cabled = board_with_cables()
    try:
        render(IMG / "board-3d-cables.png", ["--side", "top"],
               CABLE_SIZE, CABLE_ZOOM, cabled)
        render(IMG / "board-3d-iso.png", ["--side", "top", "--rotate", ISO_ROTATE],
               ISO_SIZE, ISO_ZOOM, cabled)
    finally:
        cabled.unlink(missing_ok=True)

    if missing:
        print("\nno 3D model shipped for these, so they render as bare pads:")
        for m in sorted(missing):
            print(f"  {m}")


if __name__ == "__main__":
    main()
