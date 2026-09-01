/*
 * Application-mode I2C register map. See firmware/README.md for the
 * authoritative description. Mirrored (by hand) in
 * firmware/host/rpi_camera_led.py.
 */
#ifndef FIRMWARE_COMMON_REGMAP_APP_H
#define FIRMWARE_COMMON_REGMAP_APP_H

#define REG_WHO_AM_I       0x00u  /* RO  constant, identifies app mode        */
#define REG_FW_VERSION     0x01u  /* RO  application firmware version         */
#define REG_CTRL           0x02u  /* RW  bit0/1 = copy-enable ch0/ch1         */
#define REG_GPIO_OUT       0x03u  /* RW  bit0/1 = driven output level ch0/ch1 */
#define REG_GPIO_OE        0x04u  /* RW  bit0/1 = 1:driven 0:tri-state ch0/1  */
#define REG_GPIO_IN        0x05u  /* RO  bit0/1 = live pin level ch0/ch1      */
#define REG_LED            0x06u  /* RW  LED brightness 0-255                 */
#define REG_RESERVED_07    0x07u  /* reserved, reads 0                        */
#define REG_LIGHT_LO       0x08u  /* RO  illumination, little-endian u16, LSB */
#define REG_LIGHT_HI       0x09u  /* RO  illumination, little-endian u16, MSB */
#define REG_BOOT           0x7Fu  /* WO  write REG_BOOT_MAGIC to enter the bootloader */

#define REG_APP_SIZE       0x80u  /* size of the register file exposed over I2C */

#define APP_WHO_AM_I_VALUE   0xC3u
#define APP_FW_VERSION_VALUE 0x01u

#define CTRL_COPY_EN_CH0    (1u << 0)
#define CTRL_COPY_EN_CH1    (1u << 1)

#define GPIO_CH0            (1u << 0)
#define GPIO_CH1            (1u << 1)

#define REG_BOOT_MAGIC       0xB0u

#endif /* FIRMWARE_COMMON_REGMAP_APP_H */
