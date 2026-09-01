# Bootloader image for the CH32V003J4M6 camera-LED controller.
#
# Uses ch32v003fun's build machinery for the compiler/prefix
# auto-detection, but overrides LINKER_SCRIPT with our own
# bootloader.ld (a custom 4KiB flash / cross-reset-noinit RAM layout,
# NOT the stock generated_ch32v003.ld) so ch32fun.mk's phony
# generated-linker-script rule is never invoked.

TARGET:=bootloader
TARGET_MCU:=CH32V003
CH32FUN:=../ch32v003fun/ch32fun
LINKER_SCRIPT:=bootloader.ld

include $(CH32FUN)/ch32fun.mk

# ch32fun.mk's first explicit rule is `$(TARGET).bin : $(TARGET).elf`, and
# the include is expanded before anything below it, so that rule -- not
# `all` -- would otherwise be make's default goal, and a bare `make`
# would skip the checksize guard below. Claim the default goal back.
.DEFAULT_GOAL := build

all : build

flash : cv_flash
clean : cv_clean

# Enforce the 4KiB bootloader flash budget (BOOTLOADER_SIZE in
# ../common/layout.h) independently of ch32fun.mk's own
# --print-memory-usage output, and fail the build loudly if exceeded.
.PHONY: checksize
checksize: $(TARGET).elf
	@SIZE=$$($(PREFIX)-size -A $(TARGET).elf | awk '/\.init|\.text|\.fini|\.preinit_array|\.init_array|\.fini_array|\.ctors|\.dtors|\.dlalign|\.data/ {s+=$$2} END{print s}'); \
	echo "Bootloader flash usage: $$SIZE / 4096 bytes"; \
	if [ "$$SIZE" -gt 4096 ]; then echo "ERROR: bootloader exceeds 4KiB budget"; exit 1; fi

build: checksize
