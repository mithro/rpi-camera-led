/*
 * Shared flash/RAM layout constants for the CH32V003J4M6 camera-LED
 * controller firmware. Included by BOTH the bootloader and the
 * application so the two independently-linked images agree on where
 * everything lives. Also mirrored (by hand, keep in sync) in
 * firmware/README.md and firmware/host/rpi_camera_led.py.
 *
 * Flash is 16KiB total, organised as:
 *
 *   0x0000 - 0x0FFF   bootloader (4KiB, this region is NEVER erased or
 *                     written by any code in this repository)
 *   0x1000 - 0x3FFF   application (12KiB): app code/data followed by a
 *                     16-byte trailer (app_header_t) in the very last
 *                     16 bytes of the region.
 *
 * All the addresses below are given in the CPU's *execution* address
 * space, i.e. the 0x00000000-based alias that flash is mapped to after
 * reset (see WCH RM, "boot mode"/memory remap). The flash controller
 * itself (FLASH->ADDR) wants the *physical* 0x08000000-based address,
 * so APP_FLASH_PHYS_BASE is provided separately for that use.
 */
#ifndef FIRMWARE_COMMON_LAYOUT_H
#define FIRMWARE_COMMON_LAYOUT_H

#define FLASH_TOTAL_SIZE      16384u    /* 16 KiB total flash               */
#define BOOTLOADER_SIZE       4096u     /* 4 KiB for the bootloader          */
#define APP_SIZE              (FLASH_TOTAL_SIZE - BOOTLOADER_SIZE) /* 12KiB */

#define BOOTLOADER_FLASH_BASE       0x00000000u
#define BOOTLOADER_FLASH_PHYS_BASE  0x08000000u

#define APP_FLASH_BASE               0x00001000u  /* execution alias, = BOOTLOADER_SIZE */
#define APP_FLASH_PHYS_BASE          0x08001000u  /* physical, for FLASH->ADDR */

#define FLASH_PAGE_SIZE        64u      /* CH32V003 erase granularity (bytes) */
#define APP_NUM_PAGES          (APP_SIZE / FLASH_PAGE_SIZE)  /* 192 pages */

/* The 16-byte app_header_t trailer sits in the LAST 16 bytes of the
 * LAST page of the app region, i.e. it never crosses a page boundary
 * and its address is a fixed compile-time constant independent of how
 * big the actual compiled application is. */
#define APP_HEADER_SIZE         16u
#define APP_HEADER_OFFSET       (APP_SIZE - APP_HEADER_SIZE)          /* 0x2FF0 */
#define APP_HEADER_ADDR         (APP_FLASH_BASE + APP_HEADER_OFFSET)  /* 0x3FF0 */
#define APP_HEADER_PAGE_INDEX   (APP_HEADER_OFFSET / FLASH_PAGE_SIZE) /* 191 */

#define APP_HEADER_MAGIC        0xCAFEB007u

/* RAM: 2KiB total at 0x20000000. The very first 16 bytes are reserved
 * for a NOINIT handshake word that survives a warm (PFIC/SCTLR)
 * system reset without being zeroed by crt0's .bss clear loop, used
 * by the app to ask the bootloader to stay resident for an upgrade
 * even though the currently-flashed app is valid. See README.md,
 * "Upgrade protocol / fail-safety" for why this is safe even though
 * SRAM content is *not* guaranteed valid after a real power-on. */
#define RAM_NOINIT_BASE         0x20000000u
#define RAM_NOINIT_SIZE         16u
#define RAM_BASE                (RAM_NOINIT_BASE + RAM_NOINIT_SIZE)
#define RAM_SIZE                (2048u - RAM_NOINIT_SIZE)

#define ENTER_BOOTLOADER_RAM_MAGIC  0xB007B007u

/* I2C */
#define I2C_SLAVE_ADDR           0x42u    /* 7-bit address */

#endif /* FIRMWARE_COMMON_LAYOUT_H */
