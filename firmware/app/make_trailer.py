#!/usr/bin/env python3
"""Patch the 16-byte app_header_t trailer into app.bin.

Called from the app Makefile after linking. Thin CLI wrapper around
firmware/host/app_trailer.py, which is the single source of truth for
this calculation (also used by the host-side upgrade tool) so the
build and the upgrade path can never disagree about how app_crc32 is
computed -- see that file and firmware/README.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "host"))
import app_trailer  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <app.bin>")
    path = sys.argv[1]
    with open(path, "rb") as f:
        code = f.read()
    image = app_trailer.build_trailer(code)
    with open(path, "wb") as f:
        f.write(image)
    valid, stored, computed = app_trailer.verify_trailer(image)
    assert valid and stored == computed
    print(
        f"{path}: patched app_header_t trailer, {len(code)} code bytes, "
        f"total image {len(image)} bytes, crc32=0x{computed:08x}"
    )


if __name__ == "__main__":
    main()
