#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Host-side tool for the CH32V003J4M6 camera-LED controller.

Talks to the chip over /dev/i2c-* (Linux i2c-dev, e.g. a Raspberry Pi's
I2C bus that the camera connector's I2C is wired to). No third-party
dependencies -- see i2c_raw.py, a small ctypes wrapper around the
I2C_RDWR ioctl (the same one smbus2/i2c-tools use under the hood).

Run with `uv run rpi_camera_led.py ...` (uv will use the system
Python; no packages need installing).

*** UNTESTED ON REAL HARDWARE. *** This has only been exercised
against the register maps and protocol implemented in
firmware/app/app.c and firmware/bootloader/bootloader.c by reading the
source; there is no CH32V003J4M6 board available in this environment
to verify timing, electrical behaviour, or actual I2C transaction
success/failure against silicon. Treat every command's behaviour as a
best-effort implementation of the documented protocol (firmware/README.md)
until it has been run against a real board.

Register maps mirrored (by hand -- keep in sync) from:
  firmware/common/regmap_app.h
  firmware/common/regmap_bootloader.h
  firmware/common/layout.h
"""
from __future__ import annotations

import argparse
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app_trailer  # noqa: E402
from i2c_raw import I2CBus, I2CError  # noqa: E402

DEFAULT_ADDR = 0x42  # I2C_SLAVE_ADDR, layout.h

# --- application register map (regmap_app.h) --------------------------------
REG_WHO_AM_I = 0x00
REG_FW_VERSION = 0x01
REG_CTRL = 0x02
REG_GPIO_OUT = 0x03
REG_GPIO_OE = 0x04
REG_GPIO_IN = 0x05
REG_LED = 0x06
REG_LIGHT_LO = 0x08
REG_BOOT = 0x7F

APP_WHO_AM_I_VALUE = 0xC3
REG_BOOT_MAGIC = 0xB0

CTRL_COPY_EN = {0: 1 << 0, 1: 1 << 1}
GPIO_BIT = {0: 1 << 0, 1: 1 << 1}

# --- bootloader register map (regmap_bootloader.h) ---------------------------
BREG_WHO_AM_I = 0x00
BREG_BL_VERSION = 0x01
BREG_STATUS = 0x02
BREG_CMD = 0x03
BREG_PAGE_INDEX = 0x04
BREG_PAGE_CSUM_LO = 0x05
BREG_PAGE_BUF = 0x08
BREG_APP_CRC32_0 = 0x48
BREG_APP_SIZE_0 = 0x4C

BOOTLOADER_WHO_AM_I_VALUE = 0xB1

BL_STATUS_BUSY = 1 << 0
BL_STATUS_OK = 1 << 1
BL_STATUS_ERR = 1 << 2
BL_STATUS_APP_VALID = 1 << 3

BL_CMD_NONE = 0x00
BL_CMD_PROGRAM_PAGE = 0x01
BL_CMD_VERIFY_APP = 0x02
BL_CMD_RUN_APP = 0x03

FLASH_PAGE_SIZE = app_trailer.FLASH_PAGE_SIZE
APP_NUM_PAGES = app_trailer.APP_NUM_PAGES


def crc16_ccitt_false(data: bytes) -> int:
    """Must match crc16_compute() in common/crc32.h exactly."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


class Device:
    def __init__(self, bus: I2CBus, addr: int):
        self.bus = bus
        self.addr = addr

    def read(self, reg: int, length: int) -> bytes:
        return self.bus.read_reg(self.addr, reg, length)

    def write(self, reg: int, data: bytes) -> None:
        self.bus.write_reg(self.addr, reg, data)

    def who_am_i(self) -> int:
        return self.read(REG_WHO_AM_I, 1)[0]  # same offset in both regmaps

    def mode(self) -> str:
        who = self.who_am_i()
        if who == APP_WHO_AM_I_VALUE:
            return "app"
        if who == BOOTLOADER_WHO_AM_I_VALUE:
            return "bootloader"
        return f"unknown (WHO_AM_I=0x{who:02x})"


# ------------------------------------------------------------------ app mode

def cmd_status(dev: Device, args) -> None:
    mode = dev.mode()
    print(f"mode: {mode}")
    if mode == "app":
        fw = dev.read(REG_FW_VERSION, 1)[0]
        ctrl = dev.read(REG_CTRL, 1)[0]
        gpio_out = dev.read(REG_GPIO_OUT, 1)[0]
        gpio_oe = dev.read(REG_GPIO_OE, 1)[0]
        gpio_in = dev.read(REG_GPIO_IN, 1)[0]
        led = dev.read(REG_LED, 1)[0]
        light = struct.unpack("<H", dev.read(REG_LIGHT_LO, 2))[0]
        print(f"  fw_version : {fw}")
        for ch in (0, 1):
            print(f"  ch{ch}: copy_en={bool(ctrl & CTRL_COPY_EN[ch])} "
                  f"oe={bool(gpio_oe & GPIO_BIT[ch])} "
                  f"out={bool(gpio_out & GPIO_BIT[ch])} "
                  f"in={bool(gpio_in & GPIO_BIT[ch])}")
        print(f"  led        : {led}")
        print(f"  light      : {light}")
    elif mode == "bootloader":
        _print_bootloader_status(dev)


def _print_bootloader_status(dev: Device) -> None:
    blver = dev.read(BREG_BL_VERSION, 1)[0]
    status = dev.read(BREG_STATUS, 1)[0]
    crc = struct.unpack("<L", dev.read(BREG_APP_CRC32_0, 4))[0]
    size = struct.unpack("<L", dev.read(BREG_APP_SIZE_0, 4))[0]
    print(f"  bl_version : {blver}")
    print(f"  status     : busy={bool(status & BL_STATUS_BUSY)} "
          f"ok={bool(status & BL_STATUS_OK)} err={bool(status & BL_STATUS_ERR)} "
          f"app_valid={bool(status & BL_STATUS_APP_VALID)}")
    print(f"  app crc32  : 0x{crc:08x}")
    print(f"  app size   : {size}")


def cmd_set_gpio(dev: Device, args) -> None:
    bit = GPIO_BIT[args.ch]
    reg = dev.read(REG_GPIO_OUT, 1)[0]
    reg = (reg | bit) if args.level else (reg & ~bit)
    dev.write(REG_GPIO_OUT, bytes([reg & 0xFF]))


def cmd_set_oe(dev: Device, args) -> None:
    bit = GPIO_BIT[args.ch]
    reg = dev.read(REG_GPIO_OE, 1)[0]
    reg = (reg | bit) if args.enable else (reg & ~bit)
    dev.write(REG_GPIO_OE, bytes([reg & 0xFF]))


def cmd_set_copy(dev: Device, args) -> None:
    bit = CTRL_COPY_EN[args.ch]
    reg = dev.read(REG_CTRL, 1)[0]
    reg = (reg | bit) if args.enable else (reg & ~bit)
    dev.write(REG_CTRL, bytes([reg & 0xFF]))


def cmd_set_led(dev: Device, args) -> None:
    if not 0 <= args.value <= 255:
        raise SystemExit("--value must be 0-255")
    dev.write(REG_LED, bytes([args.value]))


def cmd_get_light(dev: Device, args) -> None:
    light = struct.unpack("<H", dev.read(REG_LIGHT_LO, 2))[0]
    print(light)


def cmd_get_gpio(dev: Device, args) -> None:
    gpio_in = dev.read(REG_GPIO_IN, 1)[0]
    print(f"ch0={bool(gpio_in & GPIO_BIT[0])} ch1={bool(gpio_in & GPIO_BIT[1])}")


# --------------------------------------------------------------- bootloader

def _wait_for_mode(dev: Device, want: str, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_exc = None
    while time.monotonic() < deadline:
        try:
            if dev.mode() == want:
                return
        except I2CError as e:
            last_exc = e
        time.sleep(0.02)
    extra = f" (last error: {last_exc})" if last_exc else ""
    raise SystemExit(f"timed out waiting for device to reach mode={want}{extra}")


def cmd_enter_bootloader(dev: Device, args) -> None:
    mode = dev.mode()
    if mode == "bootloader":
        print("already in bootloader mode")
        return
    if mode != "app":
        raise SystemExit(f"unexpected mode {mode}, refusing to proceed")
    print("requesting entry to bootloader (REG_BOOT)...")
    dev.write(REG_BOOT, bytes([REG_BOOT_MAGIC]))
    # The chip does a warm reset right after acking this write; give it
    # a moment before polling again.
    time.sleep(0.05)
    _wait_for_mode(dev, "bootloader")
    print("now in bootloader mode")
    _print_bootloader_status(dev)


def _wait_not_busy(dev: Device, timeout_s: float = 1.0) -> int:
    """Poll BREG_STATUS until BUSY clears (page erase+program can take
    a few ms; see README.md). Returns the final status byte."""
    deadline = time.monotonic() + timeout_s
    status = 0
    while time.monotonic() < deadline:
        status = dev.read(BREG_STATUS, 1)[0]
        if not (status & BL_STATUS_BUSY):
            return status
        time.sleep(0.005)
    raise SystemExit("timed out waiting for BL_STATUS_BUSY to clear")


def _program_page(dev: Device, page_index: int, page_data: bytes) -> None:
    assert len(page_data) == FLASH_PAGE_SIZE
    csum = crc16_ccitt_false(page_data)
    payload = bytes([page_index, csum & 0xFF, (csum >> 8) & 0xFF, 0]) + page_data
    dev.write(BREG_PAGE_INDEX, payload)
    dev.write(BREG_CMD, bytes([BL_CMD_PROGRAM_PAGE]))
    # The bootloader does the actual erase+program in its main loop
    # (not the I2C interrupt), so it may briefly stop acking the bus.
    # Give it a little headroom before the first poll.
    time.sleep(0.01)
    status = _wait_not_busy(dev)
    if not (status & BL_STATUS_OK):
        raise SystemExit(f"page {page_index} program failed, status=0x{status:02x}")


def cmd_upgrade(dev: Device, args) -> None:
    raw = Path(args.file).read_bytes()
    if len(raw) == app_trailer.APP_SIZE:
        image = raw
        valid, stored, computed = app_trailer.verify_trailer(image)
        if not valid:
            raise SystemExit(
                f"{args.file} looks like a full app image but its trailer is "
                f"invalid (stored crc32=0x{stored:08x}, recomputed=0x{computed:08x}); "
                f"refusing to flash. Pass the raw linked app.bin instead if you "
                f"want this tool to build a fresh trailer."
            )
        print(f"using pre-built image with valid trailer (crc32=0x{stored:08x})")
    else:
        print(f"{args.file} is {len(raw)} bytes (not a full "
              f"{app_trailer.APP_SIZE}-byte trailered image) -- building trailer...")
        image = app_trailer.build_trailer(raw)
        _, crc, _ = app_trailer.verify_trailer(image)
        print(f"built image, crc32=0x{crc:08x}")

    mode = dev.mode()
    if mode == "app":
        cmd_enter_bootloader(dev, args)
    elif mode != "bootloader":
        raise SystemExit(f"unexpected mode {mode}, refusing to proceed")

    print(f"programming {APP_NUM_PAGES} pages ({app_trailer.APP_SIZE} bytes)...")
    for page_index in range(APP_NUM_PAGES):
        off = page_index * FLASH_PAGE_SIZE
        page_data = image[off:off + FLASH_PAGE_SIZE]
        _program_page(dev, page_index, page_data)
        if page_index % 16 == 0 or page_index == APP_NUM_PAGES - 1:
            print(f"  page {page_index + 1}/{APP_NUM_PAGES}")

    print("verifying app...")
    dev.write(BREG_CMD, bytes([BL_CMD_VERIFY_APP]))
    time.sleep(0.01)
    status = _wait_not_busy(dev)
    if not (status & BL_STATUS_APP_VALID):
        raise SystemExit(
            f"upgrade FAILED: app CRC32 did not verify after programming "
            f"(status=0x{status:02x}). The device will stay in the bootloader; "
            f"it is safe to retry --upgrade."
        )
    print("app verified OK, running it...")
    dev.write(BREG_CMD, bytes([BL_CMD_RUN_APP]))
    time.sleep(0.05)
    _wait_for_mode(dev, "app")
    print("upgrade complete, device is running the new app")


# ------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bus", type=int, default=1, help="I2C bus number, i.e. /dev/i2c-N (default: 1)")
    p.add_argument("--addr", type=lambda s: int(s, 0), default=DEFAULT_ADDR,
                    help=f"I2C 7-bit address (default: 0x{DEFAULT_ADDR:02x})")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="print WHO_AM_I / mode and all registers").set_defaults(func=cmd_status)

    sp = sub.add_parser("set-gpio", help="drive CAM_IOn high/low (only takes effect if OE=1 and copy-mode is off)")
    sp.add_argument("ch", type=int, choices=[0, 1])
    sp.add_argument("level", type=int, choices=[0, 1])
    sp.set_defaults(func=cmd_set_gpio)

    sp = sub.add_parser("set-oe", help="1=drive CAM_IOn, 0=tri-state/input")
    sp.add_argument("ch", type=int, choices=[0, 1])
    sp.add_argument("enable", type=int, choices=[0, 1])
    sp.set_defaults(func=cmd_set_oe)

    sp = sub.add_parser("set-copy", help="enable/disable Pi->camera GPIO passthrough (overrides OE)")
    sp.add_argument("ch", type=int, choices=[0, 1])
    sp.add_argument("enable", type=int, choices=[0, 1])
    sp.set_defaults(func=cmd_set_copy)

    sp = sub.add_parser("get-gpio", help="read live CAM_IO0/CAM_IO1 pin state")
    sp.set_defaults(func=cmd_get_gpio)

    sp = sub.add_parser("set-led", help="set LED brightness 0-255")
    sp.add_argument("value", type=int)
    sp.set_defaults(func=cmd_set_led)

    sp = sub.add_parser("get-light", help="read averaged illumination (0-1023, 10-bit ADC)")
    sp.set_defaults(func=cmd_get_light)

    sp = sub.add_parser("enter-bootloader", help="ask a running app to reset into the bootloader")
    sp.set_defaults(func=cmd_enter_bootloader)

    sp = sub.add_parser("upgrade", help="fail-safe full firmware upgrade over I2C")
    sp.add_argument("file", help="app.bin (raw linked image, or a full pre-trailered "
                                 f"{app_trailer.APP_SIZE}-byte image)")
    sp.set_defaults(func=cmd_upgrade)

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        with I2CBus(args.bus) as bus:
            dev = Device(bus, args.addr)
            args.func(dev, args)
    except I2CError as e:
        raise SystemExit(f"I2C error: {e}")


if __name__ == "__main__":
    main()
