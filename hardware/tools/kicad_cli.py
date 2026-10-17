"""Locate kicad-cli on Linux (snap), macOS and Windows.

Override with the KICAD_CLI environment variable.
"""

import os
import shutil
from pathlib import Path


def find_kicad_cli() -> str:
    env = os.environ.get("KICAD_CLI")
    if env:
        return env
    for name in ("kicad-cli", "kicad.kicad-cli"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [Path("/snap/bin/kicad.kicad-cli"),
                  Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")]
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if root:
            kicad = Path(root) / "KiCad"
            if kicad.is_dir():
                # Newest version first.
                def ver_key(p):
                    try:
                        return tuple(int(x) for x in p.name.split("."))
                    except ValueError:
                        return ()
                for ver in sorted(kicad.iterdir(), key=ver_key, reverse=True):
                    candidates.append(ver / "bin" / "kicad-cli.exe")
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError("kicad-cli not found; set the KICAD_CLI environment variable")


KICAD_CLI = find_kicad_cli()
