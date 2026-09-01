#!/bin/sh
# Run a command inside the KiCad 9 snap runtime, where the `pcbnew` Python
# module (and its python3.12 interpreter) actually live.  The snap ships no
# interpreter under /snap/kicad, so `snap run --shell` is the only way in.
#
#   hardware/tools/run_in_kicad.sh python3 hardware/tools/gen_pcb.py
set -e
cd "$(dirname "$0")/../.."
printf '%s\n' "cd '$PWD' && $*" | exec snap run --shell kicad.pcbnew
