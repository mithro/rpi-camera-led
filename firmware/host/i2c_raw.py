#!/usr/bin/env python3
"""Minimal Linux /dev/i2c-* driver using only the stdlib (ctypes + the
i2c-dev ioctl ABI), so rpi_camera_led.py has no dependency on smbus2
or any other third-party package.

Implements exactly what's needed to talk to a "register pointer,
auto-increment" I2C slave the same way i2ctransfer/i2cget/i2cset do:
a combined write-then-read using I2C_RDWR (a repeated START, not a
STOP+START) for reads, and a single write for writes.

UNTESTED ON HARDWARE -- see firmware/README.md.
"""
from __future__ import annotations

import ctypes
import fcntl
import os

I2C_SLAVE = 0x0703
I2C_RDWR = 0x0707
I2C_M_RD = 0x0001


class _i2c_msg(ctypes.Structure):
    _fields_ = [
        ("addr", ctypes.c_uint16),
        ("flags", ctypes.c_uint16),
        ("len", ctypes.c_uint16),
        ("buf", ctypes.POINTER(ctypes.c_uint8)),
    ]


class _i2c_rdwr_ioctl_data(ctypes.Structure):
    _fields_ = [
        ("msgs", ctypes.POINTER(_i2c_msg)),
        ("nmsgs", ctypes.c_uint32),
    ]


class I2CError(RuntimeError):
    pass


class I2CBus:
    """A raw I2C bus handle. Use as a context manager:

        with I2CBus(1) as bus:
            bus.write(0x42, bytes([0x00]))
            who = bus.write_read(0x42, bytes([0x00]), 1)
    """

    def __init__(self, bus_number: int):
        self.path = f"/dev/i2c-{bus_number}"
        self.fd = os.open(self.path, os.O_RDWR)

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self) -> "I2CBus":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @staticmethod
    def _mk_msg(addr: int, data: bytes, read: bool) -> tuple[_i2c_msg, ctypes.Array]:
        buf = (ctypes.c_uint8 * len(data))(*data)
        msg = _i2c_msg(
            addr=addr,
            flags=I2C_M_RD if read else 0,
            len=len(data),
            buf=ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8)),
        )
        return msg, buf  # keep buf alive alongside msg

    def _rdwr(self, msgs: list[_i2c_msg]) -> None:
        arr = (_i2c_msg * len(msgs))(*msgs)
        data = _i2c_rdwr_ioctl_data(msgs=arr, nmsgs=len(msgs))
        try:
            fcntl.ioctl(self.fd, I2C_RDWR, data)
        except OSError as e:
            raise I2CError(f"I2C_RDWR failed: {e}") from e

    def write(self, addr: int, data: bytes) -> None:
        msg, buf = self._mk_msg(addr, data, read=False)
        self._rdwr([msg])

    def write_read(self, addr: int, wdata: bytes, rlen: int) -> bytes:
        """Write wdata (typically [register_pointer, ...]), then issue
        a repeated-START read of rlen bytes -- exactly what i2cget -c
        and regmap-i2c do, and what our register-pointer I2C slave
        expects (see common/i2c_slave.h)."""
        wmsg, wbuf = self._mk_msg(addr, wdata, read=False)
        rbuf = (ctypes.c_uint8 * rlen)()
        rmsg = _i2c_msg(addr=addr, flags=I2C_M_RD, len=rlen,
                         buf=ctypes.cast(rbuf, ctypes.POINTER(ctypes.c_uint8)))
        self._rdwr([wmsg, rmsg])
        return bytes(rbuf)

    def read_reg(self, addr: int, reg: int, length: int) -> bytes:
        return self.write_read(addr, bytes([reg]), length)

    def write_reg(self, addr: int, reg: int, data: bytes) -> None:
        self.write(addr, bytes([reg]) + data)
