# Application image for the CH32V003J4M6 camera-LED controller.
#
# Same approach as ../bootloader/Makefile: reuse ch32fun.mk for
# toolchain detection but supply our own app.ld (12KiB-16B flash
# budget for code/data, starting right after the bootloader).
#
# After linking, make_trailer.py patches the 16-byte app_header_t
# (magic/size/crc32) into the last 16 bytes of app.bin so the
# bootloader can verify it -- see ../common/app_header.h and
# ../README.md.

TARGET:=app
TARGET_MCU:=CH32V003
CH32FUN:=../ch32v003fun/ch32fun
LINKER_SCRIPT:=app.ld

include $(CH32FUN)/ch32fun.mk

# ch32fun.mk's first explicit rule is `$(TARGET).bin : $(TARGET).elf`, and
# because the include is expanded before anything below it, that rule --
# not `all` -- becomes make's default goal. A bare `make` therefore
# linked the image and stopped, skipping BOTH the flash-budget check and
# the make_trailer.py step, leaving an app.bin with no app_header_t
# trailer that the bootloader would refuse to run. Claim the default
# goal back explicitly.
.DEFAULT_GOAL := build

all : build

# NOT ch32fun.mk's cv_flash. That target runs
#   minichlink -w app.bin flash -b
# and minichlink resolves the bare word "flash" to the *start* of flash
# (0x08000000), so it would write this image -- which is linked for
# APP_FLASH_BASE = 0x1000 and cannot run from 0 -- straight over the
# bootloader, bricking the board until it is reflashed over SWD.
# cv_flash also only depends on $(TARGET).bin, so it could flash an
# untrailered image that the bootloader would then refuse to run;
# depending on `build` forces the make_trailer.py step first.
flash : build $(MINICHLINK)/minichlink
	$(MINICHLINK)/minichlink -w $(TARGET).bin flash+0x1000 -b

clean : cv_clean
	rm -f app_trailer.stamp

# ch32fun.mk's $(TARGET).bin rule already produced an untrailered
# app.bin; patch it in place, then re-derive app.hex from the patched
# .bin (NOT from app.elf, which does not know about the trailer).
app_trailer.stamp: $(TARGET).bin
	uv run --no-project python3 make_trailer.py $(TARGET).bin
	$(PREFIX)-objcopy -I binary -O ihex --change-addresses 0x08001000 $(TARGET).bin $(TARGET).hex
	touch $@

.PHONY: checksize
checksize: $(TARGET).elf
	@SIZE=$$($(PREFIX)-size -A $(TARGET).elf | awk '/\.init|\.text|\.fini|\.preinit_array|\.init_array|\.fini_array|\.ctors|\.dtors|\.dlalign|\.data/ {s+=$$2} END{print s}'); \
	echo "App flash usage: $$SIZE / 12272 bytes (12288 - 16 byte trailer)"; \
	if [ "$$SIZE" -gt 12272 ]; then echo "ERROR: app exceeds its flash budget"; exit 1; fi

build: checksize app_trailer.stamp
