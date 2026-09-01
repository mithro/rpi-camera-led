/*
 * CH32V003J4M6 camera-LED controller -- fail-safe I2C bootloader.
 *
 * Runs first on every boot (it occupies flash 0x0000-0x0FFF, the
 * hardware always starts executing at address 0). It NEVER erases or
 * programs any flash address outside the application region
 * (0x1000-0x3FFF) -- see program_page() below, which is the only
 * function that touches the flash controller and is hard-bounds-
 * checked against APP_NUM_PAGES.
 *
 * Boot decision:
 *   - If the app's CRC32 (see ../common/app_header.h) is valid AND the
 *     app did not just ask to be interrupted for an upgrade, jump
 *     straight to the app.
 *   - Otherwise (invalid CRC32, blank/erased app region, or the app
 *     explicitly requested an upgrade via REG_BOOT), stay resident and
 *     serve the I2C bootloader protocol in ../common/regmap_bootloader.h
 *     until a host sends CMD_RUN_APP.
 *
 * See firmware/README.md for the full protocol description and the
 * argument for why this is safe against power loss at any point.
 */

#include "ch32fun.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "../common/layout.h"
#include "../common/regmap_bootloader.h"
#include "../common/app_header.h"
#include "../common/crc32.h"
#include "../common/i2c_slave.h"

/* Cross-reset handshake word. Lives outside [_sbss,_ebss) (see
 * bootloader.ld's .noinit section) so crt0 does not zero it, and
 * survives the PFIC/SCTLR warm reset the app uses to request entry
 * into the bootloader (see app/app.c, handle_boot_request()). It is
 * NOT relied on for fail-safety -- only the app CRC32 check is -- see
 * README.md. */
volatile uint32_t noinit_boot_flag __attribute__((section(".noinit")));

static volatile uint8_t regs[BREG_SIZE];
static volatile uint8_t pending_cmd = BL_CMD_NONE;

/* ---------------------------------------------------------------- */
/* I2C register file glue                                            */
/* ---------------------------------------------------------------- */

static void onWrite(uint8_t reg, uint8_t length)
{
	/* Was BREG_CMD written as part of this transaction? Just record
	 * the command and let main() (not interrupt context) do the
	 * actual (multi-millisecond) flash erase/program work. */
	if (reg <= BREG_CMD && (uint16_t)reg + length > BREG_CMD) {
		uint8_t cmd = regs[BREG_CMD];
		if (cmd != BL_CMD_NONE)
			pending_cmd = cmd;
	}
}

/* ---------------------------------------------------------------- */
/* Flash programming (bounds-checked to the app region ONLY)         */
/* ---------------------------------------------------------------- */

static void flash_unlock(void)
{
	FLASH->KEYR = FLASH_KEY1;
	FLASH->KEYR = FLASH_KEY2;
	FLASH->MODEKEYR = FLASH_KEY1;
	FLASH->MODEKEYR = FLASH_KEY2;
}

static void flash_lock(void)
{
	FLASH->CTLR |= CR_LOCK_Set;
}

/* Erase+program+verify exactly one FLASH_PAGE_SIZE (64 byte) page of
 * the APPLICATION region. page_index is bounds-checked against
 * APP_NUM_PAGES so this function can never touch the bootloader's own
 * 4KiB, no matter what a confused or malicious I2C host sends. */
static bool program_page(uint8_t page_index, const uint8_t *data /* 64 bytes */)
{
	if (page_index >= APP_NUM_PAGES)
		return false;

	uint32_t phys_addr = APP_FLASH_PHYS_BASE + (uint32_t)page_index * FLASH_PAGE_SIZE;

	flash_unlock();
	if (FLASH->CTLR & 0x8080) {
		/* Flash controller refused to unlock -- do not touch it. */
		flash_lock();
		return false;
	}

	/* Erase the page. */
	FLASH->CTLR = CR_PAGE_ER;
	FLASH->ADDR = phys_addr;
	FLASH->CTLR = CR_PAGE_ER | CR_STRT_Set;
	while (FLASH->STATR & FLASH_STATR_BSY)
		;

	/* Load the 64-byte page buffer, 32 bits at a time. */
	FLASH->CTLR = CR_PAGE_PG;
	FLASH->CTLR = CR_BUF_RST | CR_PAGE_PG;
	while (FLASH->STATR & FLASH_STATR_BSY)
		;
	FLASH->ADDR = phys_addr;

	const uint32_t *src32 = (const uint32_t *)(const void *)data;
	volatile uint32_t *dst32 = (volatile uint32_t *)(uintptr_t)phys_addr;
	for (uint32_t i = 0; i < FLASH_PAGE_SIZE / 4; i++) {
		dst32[i] = src32[i];
		FLASH->CTLR = CR_PAGE_PG | FLASH_CTLR_BUF_LOAD;
		while (FLASH->STATR & FLASH_STATR_BSY)
			;
	}

	/* Commit the buffer to flash. */
	FLASH->CTLR = CR_PAGE_PG | CR_STRT_Set;
	while (FLASH->STATR & FLASH_STATR_BSY)
		;

	flash_lock();

	/* Read back and verify. */
	return memcmp((const void *)(uintptr_t)phys_addr, data, FLASH_PAGE_SIZE) == 0;
}

/* ---------------------------------------------------------------- */
/* App verification                                                  */
/* ---------------------------------------------------------------- */

/* Compute the app's CRC32 exactly as the host tool must: over
 * app_used_size bytes starting at APP_FLASH_PHYS_BASE, with the
 * 4-byte crc32 field inside the header (at byte offset
 * APP_HEADER_OFFSET+8 from the start of the app region) treated as
 * zero. */
static uint32_t compute_app_crc(uint32_t app_used_size)
{
	const uint8_t *base = (const uint8_t *)(uintptr_t)APP_FLASH_PHYS_BASE;
	uint32_t crc_field_off = APP_HEADER_OFFSET + 8; /* offsetof(app_header_t, app_crc32) */
	static const uint8_t zeros[4] = {0, 0, 0, 0};

	uint32_t crc = crc32_update(0, base, crc_field_off);
	crc = crc32_update(crc, zeros, 4);
	crc = crc32_update(crc, base + crc_field_off + 4, app_used_size - (crc_field_off + 4));
	return crc;
}

/* Returns true if the app is valid and safe to run. Always updates
 * regs[BREG_APP_CRC32_*] / regs[BREG_APP_SIZE_*] with what it found. */
static bool verify_app(void)
{
	const app_header_t *hdr = (const app_header_t *)(uintptr_t)(APP_FLASH_PHYS_BASE + APP_HEADER_OFFSET);
	app_header_t h = *hdr; /* struct copy out of flash */

	uint32_t crc = 0;
	bool ok = false;

	if (h.magic == APP_HEADER_MAGIC &&
	    h.app_used_size >= APP_HEADER_SIZE &&
	    h.app_used_size <= APP_SIZE) {
		crc = compute_app_crc(h.app_used_size);
		ok = (crc == h.app_crc32);
	}

	regs[BREG_APP_CRC32_0] = (uint8_t)(crc >> 0);
	regs[BREG_APP_CRC32_1] = (uint8_t)(crc >> 8);
	regs[BREG_APP_CRC32_2] = (uint8_t)(crc >> 16);
	regs[BREG_APP_CRC32_3] = (uint8_t)(crc >> 24);
	regs[BREG_APP_SIZE_0] = (uint8_t)(h.app_used_size >> 0);
	regs[BREG_APP_SIZE_1] = (uint8_t)(h.app_used_size >> 8);
	regs[BREG_APP_SIZE_2] = (uint8_t)(h.app_used_size >> 16);
	regs[BREG_APP_SIZE_3] = (uint8_t)(h.app_used_size >> 24);

	return ok;
}

/* ---------------------------------------------------------------- */
/* Command handling (main-loop context, NOT interrupt context)       */
/* ---------------------------------------------------------------- */

typedef void (*app_entry_t)(void);

static void jump_to_app(void)
{
	__disable_irq();
	NVIC_DisableIRQ(I2C1_EV_IRQn);
	NVIC_DisableIRQ(I2C1_ER_IRQn);

	/* Reset I2C1 so the app starts from clean peripheral state. */
	RCC->APB1PRSTR |= RCC_APB1Periph_I2C1;
	RCC->APB1PRSTR &= ~RCC_APB1Periph_I2C1;

	noinit_boot_flag = 0;

	((app_entry_t)(uintptr_t)APP_FLASH_BASE)();
	/* Never returns. */
	while (1)
		;
}

static void handle_cmd(uint8_t cmd)
{
	regs[BREG_STATUS] |= BL_STATUS_BUSY;
	regs[BREG_STATUS] &= ~(BL_STATUS_OK | BL_STATUS_ERR);

	switch (cmd) {
	case BL_CMD_PROGRAM_PAGE: {
		uint8_t page_index = regs[BREG_PAGE_INDEX];
		uint16_t want_csum = (uint16_t)regs[BREG_PAGE_CSUM_LO] |
				     ((uint16_t)regs[BREG_PAGE_CSUM_HI] << 8);
		uint16_t got_csum = crc16_compute((const uint8_t *)(const void *)&regs[BREG_PAGE_BUF],
						   FLASH_PAGE_SIZE);
		bool ok = false;
		if (got_csum == want_csum) {
			uint8_t buf[FLASH_PAGE_SIZE];
			memcpy(buf, (const void *)&regs[BREG_PAGE_BUF], FLASH_PAGE_SIZE);
			ok = program_page(page_index, buf);
		}
		regs[BREG_STATUS] |= ok ? BL_STATUS_OK : BL_STATUS_ERR;
		break;
	}
	case BL_CMD_VERIFY_APP: {
		bool ok = verify_app();
		regs[BREG_STATUS] = (regs[BREG_STATUS] & ~(BL_STATUS_OK | BL_STATUS_ERR | BL_STATUS_APP_VALID)) |
				     (ok ? (BL_STATUS_OK | BL_STATUS_APP_VALID) : BL_STATUS_ERR);
		break;
	}
	case BL_CMD_RUN_APP: {
		if (regs[BREG_STATUS] & BL_STATUS_APP_VALID) {
			regs[BREG_STATUS] |= BL_STATUS_OK;
			regs[BREG_STATUS] &= ~BL_STATUS_BUSY;
			jump_to_app(); /* never returns */
		}
		regs[BREG_STATUS] |= BL_STATUS_ERR;
		break;
	}
	default:
		regs[BREG_STATUS] |= BL_STATUS_ERR;
		break;
	}

	regs[BREG_STATUS] &= ~BL_STATUS_BUSY;
}

/* ---------------------------------------------------------------- */

int main(void)
{
	SystemInit();

	bool upgrade_requested = (noinit_boot_flag == ENTER_BOOTLOADER_RAM_MAGIC);
	noinit_boot_flag = 0; /* one-shot */

	memset((void *)regs, 0, sizeof(regs));
	regs[BREG_WHO_AM_I] = BOOTLOADER_WHO_AM_I_VALUE;
	regs[BREG_BL_VERSION] = BOOTLOADER_VERSION_VALUE;

	bool app_ok = verify_app();
	if (app_ok)
		regs[BREG_STATUS] |= BL_STATUS_APP_VALID;

	if (app_ok && !upgrade_requested) {
		/* Fast path: valid app, no upgrade requested -- run it.
		 * All other GPIOs are left at their post-reset default
		 * (floating input), which is exactly the safe state the
		 * hardware requires for the bonded pins. */
		jump_to_app();
	}

	/* Stay resident: either the app is invalid/blank, or the app
	 * itself asked to be interrupted for an upgrade. Bring up I2C
	 * and serve the bootloader protocol until CMD_RUN_APP. */
	funGpioInitC();
	funPinMode(PC1, GPIO_CFGLR_OUT_10Mhz_AF_OD); /* SDA */
	funPinMode(PC2, GPIO_CFGLR_OUT_10Mhz_AF_OD); /* SCL */
	SetupI2CSlave(I2C_SLAVE_ADDR, regs, sizeof(regs), onWrite, NULL, false);

	while (1) {
		if (pending_cmd != BL_CMD_NONE) {
			uint8_t cmd = pending_cmd;
			pending_cmd = BL_CMD_NONE;
			regs[BREG_CMD] = BL_CMD_NONE;
			handle_cmd(cmd);
		}
	}
}
