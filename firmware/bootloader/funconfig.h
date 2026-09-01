#ifndef _FUNCONFIG_H
#define _FUNCONFIG_H

/* Keep the bootloader as small as possible: it has to fit comfortably
 * in a 4KiB budget alongside the flash write/erase logic and an I2C
 * slave. No UART printf debugging in the shipped build. */
#define FUNCONF_USE_DEBUGPRINTF 0
#define FUNCONF_USE_UARTPRINTF  0

#endif
