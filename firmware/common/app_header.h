/*
 * The 16-byte trailer written into the last 16 bytes of the app flash
 * region (see layout.h, APP_HEADER_ADDR / APP_HEADER_PAGE_INDEX).
 * Used by the bootloader to decide whether the flashed application is
 * safe to run, and by the host-side upgrade tool to build a correct
 * final page.
 */
#ifndef FIRMWARE_COMMON_APP_HEADER_H
#define FIRMWARE_COMMON_APP_HEADER_H

#include <stdint.h>

typedef struct {
    uint32_t magic;          /* must equal APP_HEADER_MAGIC */
    uint32_t app_used_size;  /* bytes of real app image, from APP_FLASH_BASE,
                               * INCLUDING this header, i.e. always
                               * <= APP_SIZE. CRC32 below covers exactly
                               * this many bytes. */
    uint32_t app_crc32;      /* CRC-32/ISO-HDLC (the common "zlib" CRC32:
                               * poly 0xEDB88320, init 0, no final xor as
                               * implemented here -- see crc32.h) of the
                               * app_used_size bytes starting at
                               * APP_FLASH_BASE, computed with THIS FIELD
                               * treated as zero during the calculation. */
    uint32_t reserved;       /* must be 0, reserved for future use */
} app_header_t;

#endif /* FIRMWARE_COMMON_APP_HEADER_H */
