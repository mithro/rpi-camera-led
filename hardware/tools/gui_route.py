#!/usr/bin/env python3
"""Drive the pcbnew GUI with synthetic X11 input (xdotool).

Used to route hardware/rpi-camera-led.kicad_pcb interactively inside a private
Xvfb display.  Board millimetres are mapped to screen pixels with an affine
transform that is measured from pcbnew's own cursor read-out, so the mapping
stays honest across zoom/pan changes.

    # measure the mm -> pixel transform (reads two probe points by hand)
    uv run hardware/tools/gui_route.py probe 700 500
    uv run hardware/tools/gui_route.py setxform <x0> <y0> <x1> <y1> <mmx0> <mmy0> <mmx1> <mmy1>

    # route one track: start pad, waypoints, end pad
    uv run hardware/tools/gui_route.py route --layer B.Cu --width 0.15 \
        26.2,25.931 23.5,25.931 23.5,37.931 38.8,37.931

    # misc
    uv run hardware/tools/gui_route.py shot out.png [x y w h]
    uv run hardware/tools/gui_route.py key ctrl+s
"""

import json
import os
import subprocess
import sys
import time

DISPLAY = os.environ.get("PCBNEW_DISPLAY", ":77")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
XFORM = os.path.join(REPO, "tmp", "xform.json")


def xdo(*args):
    subprocess.run(["xdotool"] + [str(a) for a in args],
                   env=dict(os.environ, DISPLAY=DISPLAY), check=True)


def load_xform():
    with open(XFORM) as fh:
        return json.load(fh)


def mm2px(x, y, t=None):
    t = t or load_xform()
    return int(round(t["ax"] + t["s"] * x)), int(round(t["ay"] + t["s"] * y))


def cmd_setxform(argv):
    x0, y0, x1, y1, mx0, my0, mx1, my1 = [float(v) for v in argv]
    sx = (x1 - x0) / (mx1 - mx0)
    sy = (y1 - y0) / (my1 - my0)
    s = (sx + sy) / 2.0
    t = {"s": s, "ax": x0 - s * mx0, "ay": y0 - s * my0, "sx": sx, "sy": sy}
    os.makedirs(os.path.dirname(XFORM), exist_ok=True)
    with open(XFORM, "w") as fh:
        json.dump(t, fh, indent=1)
    print("scale %.4f px/mm (sx %.4f sy %.4f)  origin px (%.1f, %.1f)"
          % (s, sx, sy, t["ax"], t["ay"]))
    for mm in ((20, 20), (32.5, 31.931), (45, 43.862)):
        print("  %8.3f,%8.3f mm -> %s px" % (mm[0], mm[1], mm2px(mm[0], mm[1], t)))


def cmd_probe(argv):
    xdo("mousemove", argv[0], argv[1])
    time.sleep(0.6)


def cmd_shot(argv):
    out = argv[0]
    crop = []
    if len(argv) >= 5:
        crop = ["-crop", "%sx%s+%s+%s" % (argv[3], argv[4], argv[1], argv[2]), "+repage"]
    subprocess.run(["import", "-window", "root"] + crop + [out],
                   env=dict(os.environ, DISPLAY=DISPLAY), check=True)


def cmd_key(argv):
    for k in argv:
        xdo("key", k)
        time.sleep(0.25)


def cmd_click(argv):
    x, y = mm2px(float(argv[0].split(",")[0]), float(argv[0].split(",")[1]))
    xdo("mousemove", x, y)
    time.sleep(0.25)
    xdo("click", argv[1] if len(argv) > 1 else "1")
    time.sleep(0.3)


LAYER_KEY = {"F.Cu": "Page_Up", "B.Cu": "Page_Down"}


def cmd_route(argv):
    layer = None
    width = None
    pts = []
    i = 0
    while i < len(argv):
        if argv[i] == "--layer":
            layer = argv[i + 1]
            i += 2
        elif argv[i] == "--width":
            width = argv[i + 1]
            i += 2
        else:
            xs, ys = argv[i].split(",")
            pts.append((float(xs), float(ys)))
            i += 1
    if len(pts) < 2:
        raise SystemExit("need at least a start and an end point")

    t = load_xform()
    xdo("key", "Escape")
    time.sleep(0.3)
    if layer:
        xdo("key", LAYER_KEY[layer])
        time.sleep(0.3)

    # Park the cursor on the start pad, then arm the single-track router: the
    # router picks up whatever is under the cursor, which snaps to the pad.
    sx, sy = mm2px(pts[0][0], pts[0][1], t)
    xdo("mousemove", sx, sy)
    time.sleep(0.4)
    xdo("key", "x")
    time.sleep(0.6)

    for p in pts[1:-1]:
        px, py = mm2px(p[0], p[1], t)
        xdo("mousemove", px, py)
        time.sleep(0.35)
        xdo("click", "1")
        time.sleep(0.35)

    ex, ey = mm2px(pts[-1][0], pts[-1][1], t)
    xdo("mousemove", ex, ey)
    time.sleep(0.4)
    xdo("click", "--repeat", "2", "--delay", "80", "1")
    time.sleep(0.6)
    xdo("key", "Escape")
    time.sleep(0.3)


def cmd_via(argv):
    """Route to a point, drop a via there, and finish (layer change mid-track)."""
    layer = None
    pts = []
    i = 0
    while i < len(argv):
        if argv[i] == "--layer":
            layer = argv[i + 1]
            i += 2
        else:
            xs, ys = argv[i].split(",")
            pts.append((float(xs), float(ys)))
            i += 1
    t = load_xform()
    xdo("key", "Escape")
    time.sleep(0.3)
    if layer:
        xdo("key", LAYER_KEY[layer])
        time.sleep(0.3)
    sx, sy = mm2px(pts[0][0], pts[0][1], t)
    xdo("mousemove", sx, sy)
    time.sleep(0.4)
    xdo("key", "x")
    time.sleep(0.6)
    for p in pts[1:]:
        px, py = mm2px(p[0], p[1], t)
        xdo("mousemove", px, py)
        time.sleep(0.35)
        xdo("click", "1")
        time.sleep(0.35)
    xdo("key", "v")          # drop a via and swap to the other copper layer
    time.sleep(0.5)
    xdo("key", "Escape")
    time.sleep(0.4)
    xdo("key", "Escape")
    time.sleep(0.3)


def cmd_path(argv):
    """Route one track that may change layer part way.

    Tokens are "x,y" board millimetres, or "v" to drop a via at the next fixed
    point (which swaps the active copper layer).  The first token is the start
    pad, the last is the end.  pcbnew needs generous settling time between
    synthetic events or it drops them, hence the sleeps.
    """
    layer = None
    toks = []
    i = 0
    while i < len(argv):
        if argv[i] == "--layer":
            layer = argv[i + 1]
            i += 2
        else:
            toks.append(argv[i])
            i += 1

    t = load_xform()
    # A modifier left held down by an earlier accelerator turns every click
    # into ctrl/shift-click, which the router quietly ignores.
    xdo("keyup", "ctrl", "shift", "alt", "super")
    time.sleep(0.2)
    xdo("key", "Escape")
    time.sleep(0.45)
    xdo("key", "Escape")
    time.sleep(0.45)
    if layer:
        xdo("key", LAYER_KEY[layer])
        time.sleep(0.45)

    def go(tok):
        xs, ys = tok.split(",")
        px, py = mm2px(float(xs), float(ys), t)
        xdo("mousemove", px, py)
        time.sleep(0.6)

    go(toks[0])
    xdo("key", "x")
    time.sleep(0.9)

    for tok in toks[1:]:
        if tok in ("v", "pgdn", "pgup"):
            xdo("key", {"v": "v", "pgdn": "Page_Down", "pgup": "Page_Up"}[tok])
            time.sleep(0.7)
            continue
        go(tok)
        xdo("click", "1")
        time.sleep(0.7)

    xdo("key", "Escape")
    time.sleep(0.5)
    xdo("key", "Escape")
    time.sleep(0.4)


COMMANDS = {
    "path": cmd_path,
    "setxform": cmd_setxform,
    "probe": cmd_probe,
    "shot": cmd_shot,
    "key": cmd_key,
    "click": cmd_click,
    "route": cmd_route,
    "via": cmd_via,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
