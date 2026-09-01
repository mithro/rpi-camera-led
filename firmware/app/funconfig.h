#ifndef _FUNCONFIG_H
#define _FUNCONFIG_H

/* No UART printf debugging in the shipped build (flash is tight and
 * PD5/PD6 are in use for the camera GPIO passthrough / bonded pins). */
#define FUNCONF_USE_DEBUGPRINTF 0
#define FUNCONF_USE_UARTPRINTF  0

#endif
