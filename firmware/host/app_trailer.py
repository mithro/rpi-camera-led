#!/usr/bin/env python3
"""Shared app_header_t / CRC32 logic for the CH32V003 camera-LED app image.

This is the single source of truth used both by the build system
(firmware/app/make_trailer.py, run after every `make` of the app
image) and by the host upgrade tool (rpi_camera_led.py's --upgrade),
so the two can never disagree about how app_crc32 is computed.

It mirrors firmware/bootloader/bootloader.c's compute_app_crc()
byte-for-byte: CRC32 (the zlib/CRC-32/ISO-HDLC variant) over the
*entire* APP_SIZE-byte app region (code, padded with 0xFF, followed by
the 16-byte header: magic, app_used_size, crc32, reserved) with the
crc32 field itself substituted with 4 zero bytes during the
calculation. See ../common/app_header.h and ../README.md.
"""
from __future__ import annotations

import struct
import zlib

APP_SIZE = 12288
APP_HEADER_SIZE = 16
APP_HEADER_OFFSET = APP_SIZE - APP_HEADER_SIZE  # 12272: code budget
APP_HEADER_MAGIC = 0xCAFEB007
FLASH_PAGE_SIZE = 64
APP_NUM_PAGES = APP_SIZE // FLASH_PAGE_SIZE  # 192
APP_HEADER_PAGE_INDEX = APP_HEADER_OFFSET // FLASH_PAGE_SIZE  # 191


def pad_code(code: bytes) -> bytes:
    """Pad a raw app.bin (just the linked code/data, no trailer) up to
    APP_HEADER_OFFSET bytes with 0xFF (erased-flash value)."""
    if len(code) > APP_HEADER_OFFSET:
        raise ValueError(
            f"app image is {len(code)} bytes, exceeds the "
            f"{APP_HEADER_OFFSET}-byte budget before the header trailer"
        )
    return code + b"\xff" * (APP_HEADER_OFFSET - len(code))


def compute_app_crc32(padded_code: bytes, app_used_size: int) -> int:
    """CRC32 over app_used_size bytes: padded_code (APP_HEADER_OFFSET
    bytes) followed by the header's magic + app_used_size fields, a
    zeroed crc32 field, and the reserved field -- exactly what
    bootloader.c's compute_app_crc() walks over in flash."""
    if len(padded_code) != APP_HEADER_OFFSET:
        raise ValueError(f"padded_code must be exactly {APP_HEADER_OFFSET} bytes")
    crc = zlib.crc32(padded_code) & 0xFFFFFFFF
    crc = zlib.crc32(struct.pack("<L", APP_HEADER_MAGIC), crc) & 0xFFFFFFFF
    crc = zlib.crc32(struct.pack("<L", app_used_size), crc) & 0xFFFFFFFF
    crc = zlib.crc32(b"\x00\x00\x00\x00", crc) & 0xFFFFFFFF  # crc32 field, zeroed
    crc = zlib.crc32(struct.pack("<L", 0), crc) & 0xFFFFFFFF  # reserved field
    return crc


def build_trailer(code: bytes) -> bytes:
    """Return a full APP_SIZE-byte flash image for the app region:
    code padded to APP_HEADER_OFFSET with 0xFF, followed by the
    16-byte app_header_t trailer with a correct CRC32."""
    padded_code = pad_code(code)
    app_used_size = APP_SIZE
    crc = compute_app_crc32(padded_code, app_used_size)
    header = struct.pack("<LLLL", APP_HEADER_MAGIC, app_used_size, crc, 0)
    image = padded_code + header
    assert len(image) == APP_SIZE
    return image


def verify_trailer(image: bytes) -> tuple[bool, int, int]:
    """Given a full APP_SIZE-byte image, recompute its CRC32 the same
    way the bootloader does and report (valid, stored_crc, computed_crc)."""
    if len(image) != APP_SIZE:
        raise ValueError(f"image must be exactly {APP_SIZE} bytes, got {len(image)}")
    padded_code = image[:APP_HEADER_OFFSET]
    magic, app_used_size, stored_crc, reserved = struct.unpack(
        "<LLLL", image[APP_HEADER_OFFSET:]
    )
    if magic != APP_HEADER_MAGIC or app_used_size != APP_SIZE:
        return (False, stored_crc, 0)
    computed = compute_app_crc32(padded_code, app_used_size)
    return (computed == stored_crc, stored_crc, computed)
