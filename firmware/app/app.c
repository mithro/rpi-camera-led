/*
 * CH32V003J4M6 camera-LED controller -- application.
 *
 * See firmware/README.md for the full pin map and register map. Short
 * version:
 *
 *   PD6 (bonded w/ PA1)  -> CAM_IO0, driven output or tri-state input
 *   PA2                  -> CAM_IO1, driven output or tri-state input
 *   PC1/PC2               -> I2C1 SDA/SCL (slave, address I2C_SLAVE_ADDR)
 *   PC4                   -> ADC1 channel A2, phototransistor light sensor
 *   PD1 (bonded w/ PD4,PD5) -> TIM1 CH3N hardware PWM, white LED gate
 *
 * PA1, PD4 and PD5 are the *unused* halves of pins that are bonded to
 * two ports inside the SOP-8 package (see README.md, "Hardware") and
 * are kept as floating inputs for the whole lifetime of this program
 * so they never fight the pin they're bonded to.
 */

#include "ch32fun.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "../common/layout.h"
#include "../common/regmap_app.h"
#include "../common/i2c_slave.h"

/* Same cross-reset handshake word as the bootloader -- see
 * bootloader/bootloader.c and app.ld's .noinit section. */
volatile uint32_t noinit_boot_flag __attribute__((section(".noinit")));

static volatile uint8_t regs[REG_APP_SIZE];
static volatile bool boot_requested = false;

/* ---------------------------------------------------------------- */
/* I2C register file glue                                            */
/* ---------------------------------------------------------------- */

static void onWrite(uint8_t reg, uint8_t length)
{
	if (reg <= REG_BOOT && (uint16_t)reg + length > REG_BOOT) {
		if (regs[REG_BOOT] == REG_BOOT_MAGIC)
			boot_requested = true;
		regs[REG_BOOT] = 0;
	}
}

/* ---------------------------------------------------------------- */
/* GPIO passthrough / drive (CAM_IO0 = PD6, CAM_IO1 = PA2)           */
/* ---------------------------------------------------------------- */

static void update_gpio_channel(uint32_t pin, uint8_t bit)
{
	bool copy_en = regs[REG_CTRL] & bit;
	bool oe = regs[REG_GPIO_OE] & bit;
	bool out_level = regs[REG_GPIO_OUT] & bit;

	/* Copy mode always wins: force tri-state so the Pi's own GPIO
	 * state (through the 10k) reaches the camera unmodified. */
	if (copy_en || !oe) {
		funPinMode(pin, GPIO_CFGLR_IN_FLOAT);
	} else {
		/* Load OUTDR *before* enabling the output driver. OUTDR
		 * keeps whatever was last written to it (0 out of reset),
		 * so configuring the pin as a push-pull output first would
		 * drive the stale level onto the camera's GPIO for the few
		 * cycles until funDigitalWrite() caught up -- a real glitch
		 * on every 0->1 transition of GPIO_OE. Writing OUTDR while
		 * the pin is still a floating input has no effect on the
		 * pin (OUTDR only selects the pull direction in the
		 * pull-up/pull-down input modes, which this is not). */
		funDigitalWrite(pin, out_level ? FUN_HIGH : FUN_LOW);
		funPinMode(pin, GPIO_CFGLR_OUT_10Mhz_PP);
	}

	/* Live pin read: reflects the Pi's passed-through state when
	 * tri-stated (copy mode or OE=0), or the value we're driving
	 * when OE=1 and copy mode is off -- see README.md. */
	if (funDigitalRead(pin))
		regs[REG_GPIO_IN] |= bit;
	else
		regs[REG_GPIO_IN] &= ~bit;
}

/* ---------------------------------------------------------------- */
/* ADC (PC4 / ANALOG_2), continuously sampled + averaged              */
/* ---------------------------------------------------------------- */

/* SysTick does NOT run at the core clock by default: ch32fun's
 * handle_reset() writes SysTick->CTLR = 1 (HCLK/8) unless
 * FUNCONF_SYSTICK_USE_HCLK is set, in which case it writes 5 (HCLK).
 * See the "SYSTICK info" block in ch32fun.h. Derive the tick rate
 * instead of assuming it equals FUNCONF_SYSTEM_CORE_CLOCK, or the
 * sample period silently comes out 8x too long. */
#if defined(FUNCONF_SYSTICK_USE_HCLK) && FUNCONF_SYSTICK_USE_HCLK
#define SYSTICK_HZ (FUNCONF_SYSTEM_CORE_CLOCK)
#else
#define SYSTICK_HZ (FUNCONF_SYSTEM_CORE_CLOCK / 8u)
#endif

#define LIGHT_SAMPLE_HZ 100u
#define LIGHT_SAMPLE_PERIOD_TICKS (SYSTICK_HZ / LIGHT_SAMPLE_HZ)
#define LIGHT_EMA_SHIFT 3 /* averages over 2^3 = 8 samples */

static void adc_init(void)
{
	RCC->CFGR0 &= ~(0x1Fu << 11); /* ADCCLK = HCLK/2 */
	RCC->APB2PCENR |= RCC_APB2Periph_ADC1;

	RCC->APB2PRSTR |= RCC_APB2Periph_ADC1;
	RCC->APB2PRSTR &= ~RCC_APB2Periph_ADC1;

	funPinMode(PC4, GPIO_CFGLR_IN_ANALOG);

	ADC1->RSQR1 = 0;
	ADC1->RSQR2 = 0;
	ADC1->RSQR3 = ANALOG_2;

	ADC1->SAMPTR2 &= ~(ADC_SMP0 << (3 * ANALOG_2));
	ADC1->SAMPTR2 |= (uint32_t)7 << (3 * ANALOG_2); /* longest sample time */

	ADC1->CTLR2 |= ADC_ADON | ADC_EXTSEL;

	ADC1->CTLR2 |= CTLR2_RSTCAL_Set;
	while (ADC1->CTLR2 & CTLR2_RSTCAL_Set)
		;
	ADC1->CTLR2 |= CTLR2_CAL_Set;
	while (ADC1->CTLR2 & CTLR2_CAL_Set)
		;
}

static uint16_t adc_sample(void)
{
	ADC1->CTLR2 |= ADC_SWSTART;
	while (!(ADC1->STATR & ADC_EOC))
		;
	return (uint16_t)ADC1->RDATAR;
}

static void light_poll(void)
{
	static uint32_t last_tick;
	/* Accumulator held scaled by 2^LIGHT_EMA_SHIFT. Doing the average
	 * as `ema += (sample - ema) >> SHIFT` on an unscaled value instead
	 * loses the low bits of every update, so the filter stalls short
	 * of its input (a steady 1023 settles at ~1016 and full scale is
	 * never reachable). */
	static int32_t acc;
	static bool primed = false;

	uint32_t now = funSysTick32();
	if (primed && (now - last_tick) < LIGHT_SAMPLE_PERIOD_TICKS)
		return;
	last_tick = now;

	int32_t sample = adc_sample();
	if (!primed) {
		acc = sample << LIGHT_EMA_SHIFT; /* start at the first reading */
		primed = true;
	} else {
		acc += sample - (acc >> LIGHT_EMA_SHIFT);
	}

	uint16_t v = (uint16_t)(acc >> LIGHT_EMA_SHIFT);
	/* Publish both halves atomically with respect to the I2C
	 * interrupt, so a host reading LIGHT_LO..LIGHT_HI in one burst
	 * can never get the low byte of one sample and the high byte of
	 * the next. */
	__disable_irq();
	regs[REG_LIGHT_LO] = (uint8_t)(v & 0xFF);
	regs[REG_LIGHT_HI] = (uint8_t)(v >> 8);
	__enable_irq();
}

/* ---------------------------------------------------------------- */
/* LED PWM (PD1 = TIM1 CH3N, NOREMAP mapping)                        */
/* ---------------------------------------------------------------- */

/* PSC=186 (divide by 187) with ATRLR=255 (256 counts) gives
 * 48MHz / 187 / 256 =~ 1.003kHz PWM, and lets an 8-bit brightness
 * value map 1:1 onto the compare register. */
#define LED_PWM_PSC   186
#define LED_PWM_ATRLR 255

static void led_pwm_init(void)
{
	RCC->APB2PCENR |= RCC_APB2Periph_TIM1 | RCC_APB2Periph_AFIO;

	/* NOREMAP mapping already puts T1CH3N on PD1 -- no AFIO remap
	 * needed (see tim1_pwm_complementary_outputs example in the
	 * ch32v003fun submodule for the full remap table). */
	funPinMode(PD1, GPIO_CFGLR_OUT_10Mhz_AF_PP);

	RCC->APB2PRSTR |= RCC_APB2Periph_TIM1;
	RCC->APB2PRSTR &= ~RCC_APB2Periph_TIM1;

	TIM1->CTLR1 = 0;
	TIM1->CTLR2 = 0;
	TIM1->PSC = LED_PWM_PSC;
	TIM1->ATRLR = LED_PWM_ATRLR;
	TIM1->SWEVGR |= TIM_UG;

	TIM1->CCER |= TIM_CC3E | TIM_CC3P | TIM_CC3NE | TIM_CC3NP;
	TIM1->CHCTLR2 |= TIM_OC3M_1 | TIM_OC3M_2; /* PWM mode 1 */
	TIM1->CH3CVR = 0;

	TIM1->BDTR |= TIM_MOE;
	TIM1->CTLR1 |= TIM_CEN;
}

static void led_pwm_set(uint8_t brightness)
{
	TIM1->CH3CVR = brightness;
}

/* ---------------------------------------------------------------- */

int main(void)
{
	SystemInit();

	memset((void *)regs, 0, sizeof(regs));
	regs[REG_WHO_AM_I] = APP_WHO_AM_I_VALUE;
	regs[REG_FW_VERSION] = APP_FW_VERSION_VALUE;

	funGpioInitAll();

	/* Defensively (re)assert the bonded-but-unused halves of pin 1
	 * and pin 8 as floating inputs, even though this is also the
	 * post-reset default -- see the file header comment. */
	funPinMode(PA1, GPIO_CFGLR_IN_FLOAT);
	funPinMode(PD4, GPIO_CFGLR_IN_FLOAT);
	funPinMode(PD5, GPIO_CFGLR_IN_FLOAT);

	/* CAM_IO0/CAM_IO1 start tri-stated (OE defaults to 0 in regs). */

	adc_init();
	led_pwm_init();

	funPinMode(PC1, GPIO_CFGLR_OUT_10Mhz_AF_OD); /* SDA */
	funPinMode(PC2, GPIO_CFGLR_OUT_10Mhz_AF_OD); /* SCL */
	SetupI2CSlave(I2C_SLAVE_ADDR, regs, sizeof(regs), onWrite, NULL, false);

	while (1) {
		/* The I2C slave driver has a single read_only flag for the
		 * whole register file, and this file must be writable
		 * (CTRL / GPIO_OUT / GPIO_OE / LED / BOOT), so a host can
		 * write the read-only registers too. Re-stamp the constant
		 * ones every pass; GPIO_IN and LIGHT are overwritten by
		 * their own producers below. */
		regs[REG_WHO_AM_I] = APP_WHO_AM_I_VALUE;
		regs[REG_FW_VERSION] = APP_FW_VERSION_VALUE;
		regs[REG_RESERVED_07] = 0;

		update_gpio_channel(PD6, GPIO_CH0);
		update_gpio_channel(PA2, GPIO_CH1);

		light_poll();

		led_pwm_set(regs[REG_LED]);

		if (boot_requested) {
			boot_requested = false;
			noinit_boot_flag = ENTER_BOOTLOADER_RAM_MAGIC;
			PFIC->SCTLR = 1u << 31; /* system reset; bootloader runs next */
			while (1)
				;
		}
	}
}
