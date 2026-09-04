# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Regenerate the board images that README.md embeds.

Writes three files into docs/img/:

    board-3d-top.png     raytraced 3D render, viewed from the front
    board-3d-bottom.png  the same from the back
    board-layout.svg     F.Cu / B.Cu / F.SilkS / Edge.Cuts, board area only

The 3D views are deliberately zoomed out far enough to include every
footprint, not just the ones inside the board outline -- eleven parts are
still sitting off the board while the layout is in progress, and cropping
them out of the README would make the board look more finished than it is.

Usage (from the repository root):
    uv run hardware/tools/render_board.py
"""

import re
import subprocess
import sys
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
PCB = HW / "rpi-camera-led.kicad_pcb"
IMG = HW.parent / "docs" / "img"

KICAD_CLI = "/snap/bin/kicad.kicad-cli"
# kicad-cli does not inherit the GUI's path substitutions, so the models
# resolve to nothing unless this is handed to it explicitly.
MODEL_DIR = "/snap/kicad/current/usr/share/kicad/3dmodels"

# The three images sit side by side in the README, so they are given a common
# aspect ratio: the SVG's page is whatever KiCad's "board area only" mode
# computes, and the 3D renders are widened to match it.  Deriving the width
# instead of hardcoding it keeps them matched if the board outline changes.
HEIGHT = 1500
ZOOM = "0.45"  # fits the off-board footprints too; see the note above
LAYERS = "F.Cu,B.Cu,F.SilkS,Edge.Cuts"


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"failed: {' '.join(args)}")
    return r


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    missing = set()

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

    for side in ("top", "bottom"):
        out = IMG / f"board-3d-{side}.png"
        r = run([KICAD_CLI, "pcb", "render", "-o", str(out),
                 "--side", side, "--width", str(width), "--height", str(HEIGHT),
                 "--quality", "high", "--background", "opaque", "--zoom", ZOOM,
                 "-D", f"KICAD9_3DMODEL_DIR={MODEL_DIR}", str(PCB)])
        # KiCad reports the miss on stderr, as a wxWidgets trace line.
        for line in (r.stdout + r.stderr).splitlines():
            if "could not find model" in line:
                missing.add(line.split("'")[1] if "'" in line else line.strip())
        print(f"{out.relative_to(HW.parent)}  ({out.stat().st_size // 1024} KiB, "
              f"{width} x {HEIGHT} px)")

    if missing:
        print("\nno 3D model shipped for these, so they render as bare pads:")
        for m in sorted(missing):
            print(f"  {m}")


if __name__ == "__main__":
    main()
