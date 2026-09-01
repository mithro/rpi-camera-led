/*
 * Bootloader-mode I2C register/command map. Exposed at the SAME I2C
 * slave address as the application (I2C_SLAVE_ADDR) since the two are
 * never active at the same time -- read REG_WHO_AM_I to find out which
 * one you are currently talking to. See firmware/README.md, "Upgrade
 * protocol" for the full sequence a host must follow.
 */
#ifndef FIRMWARE_COMMON_REGMAP_BOOTLOADER_H
#define FIRMWARE_COMMON_REGMAP_BOOTLOADER_H

#define BREG_WHO_AM_I       0x00u  /* RO  constant, identifies bootloader mode */
#define BREG_BL_VERSION     0x01u  /* RO  bootloader version                   */
#define BREG_STATUS         0x02u  /* RO  status bits, see BL_STATUS_*         */
#define BREG_CMD            0x03u  /* WO  write a BL_CMD_* value to execute    */
#define BREG_PAGE_INDEX     0x04u  /* RW  u8, page number within app region    */
#define BREG_PAGE_CSUM_LO   0x05u  /* RW  CRC16 of PAGE_BUF, little-endian LSB */
#define BREG_PAGE_CSUM_HI   0x06u  /* RW  CRC16 of PAGE_BUF, little-endian MSB */
#define BREG_RESERVED_07    0x07u  /* reserved, reads 0                        */
#define BREG_PAGE_BUF       0x08u  /* RW  64-byte page data buffer             */
#define BREG_PAGE_BUF_END   (BREG_PAGE_BUF + 64u) /* = 0x48, one past the end  */
#define BREG_APP_CRC32_0    0x48u  /* RO  last-computed app CRC32, LE, byte 0  */
#define BREG_APP_CRC32_1    0x49u
#define BREG_APP_CRC32_2    0x4Au
#define BREG_APP_CRC32_3    0x4Bu
#define BREG_APP_SIZE_0     0x4Cu  /* RO  app_header_t.app_used_size, LE       */
#define BREG_APP_SIZE_1     0x4Du
#define BREG_APP_SIZE_2     0x4Eu
#define BREG_APP_SIZE_3     0x4Fu

#define BREG_SIZE           0x50u  /* size of the register file exposed over I2C */

#define BOOTLOADER_WHO_AM_I_VALUE   0xB1u
#define BOOTLOADER_VERSION_VALUE    0x01u

/* BREG_STATUS bits */
#define BL_STATUS_BUSY       (1u << 0) /* flash op (from a previous CMD) in progress */
#define BL_STATUS_OK         (1u << 1) /* last flash op / verify completed OK        */
#define BL_STATUS_ERR        (1u << 2) /* last flash op / verify failed              */
#define BL_STATUS_APP_VALID  (1u << 3) /* most recent CMD_VERIFY_APP found the app CRC32 valid */

/* BREG_CMD values (write-only "command register") */
#define BL_CMD_NONE           0x00u
#define BL_CMD_PROGRAM_PAGE   0x01u /* erase+program+verify page BREG_PAGE_INDEX from BREG_PAGE_BUF, checked against BREG_PAGE_CSUM */
#define BL_CMD_VERIFY_APP     0x02u /* recompute app CRC32, update BL_STATUS_APP_VALID + BREG_APP_CRC32/BREG_APP_SIZE */
#define BL_CMD_RUN_APP        0x03u /* if BL_STATUS_APP_VALID, jump to the application */

#endif /* FIRMWARE_COMMON_REGMAP_BOOTLOADER_H */
