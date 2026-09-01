#!/usr/bin/env python3
"""Summarise `kicad-cli pcb drc --format json` output while routing."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PCB = REPO / "hardware" / "rpi-camera-led.kicad_pcb"
OUT = REPO / "tmp" / "drc.json"


def main():
    OUT.parent.mkdir(exist_ok=True)
    subprocess.run(["/snap/bin/kicad.kicad-cli", "pcb", "drc",
                    "--severity-error", "--format", "json", "-o", str(OUT), str(PCB)],
                   check=True, stdout=subprocess.DEVNULL)
    d = json.loads(OUT.read_text())
    viol = d.get("violations", [])
    unc = d.get("unconnected_items", [])
    print("violations: %d   unconnected: %d" % (len(viol), len(unc)))
    for v in viol:
        pos = ", ".join("%s @ %.2f,%.2f" % (i["description"], i["pos"]["x"], i["pos"]["y"])
                        for i in v.get("items", []))
        print("  ERR %-28s %s | %s" % (v["type"], v["description"], pos))
    for u in unc:
        parts = []
        for i in u["items"]:
            parts.append("%s @ %.3f,%.3f" % (i["description"], i["pos"]["x"], i["pos"]["y"]))
        print("  UNC %s" % "  <->  ".join(parts))
    return 1 if (viol or unc) else 0


if __name__ == "__main__":
    sys.exit(main())
