/*
 * Minimal, table-free CRC-32 (the ubiquitous "CRC-32/ISO-HDLC" a.k.a.
 * zlib/PNG/Ethernet CRC32: polynomial 0xEDB88320, reflected, init
 * 0xFFFFFFFF, final XOR 0xFFFFFFFF) and CRC-16/CCITT-FALSE.
 *
 * crc32() below is written so that crc32(data, len) called once over a
 * whole buffer produces EXACTLY the same result as Python's
 * zlib.crc32(data) / binascii.crc32(data) -- this is relied on by
 * firmware/host/rpi_camera_led.py to compute a matching app_crc32.
 *
 * Bit-banged rather than table-driven to keep code size down on a
 * chip with 16KiB of flash total; called only a handful of times
 * (boot-time app verify, and once per page during an upgrade) so the
 * extra cycles do not matter.
 */
#ifndef FIRMWARE_COMMON_CRC32_H
#define FIRMWARE_COMMON_CRC32_H

#include <stdint.h>
#include <stddef.h>

static inline uint32_t crc32_compute(const uint8_t *data, uint32_t len)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++) {
            uint32_t mask = -(int32_t)(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return crc ^ 0xFFFFFFFFu;
}

/* CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no
 * final xor). Used only as a cheap per-page transport-integrity check
 * between host and bootloader; it does not need to match any
 * particular "standard" name as long as both sides agree, but this is
 * a well known variant so off-the-shelf host libraries can be used
 * too. */
static inline uint16_t crc16_compute(const uint8_t *data, uint32_t len)
{
    uint16_t crc = 0xFFFFu;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; b++) {
            if (crc & 0x8000u)
                crc = (uint16_t)((crc << 1) ^ 0x1021u);
            else
                crc = (uint16_t)(crc << 1);
        }
    }
    return crc;
}

#endif /* FIRMWARE_COMMON_CRC32_H */
