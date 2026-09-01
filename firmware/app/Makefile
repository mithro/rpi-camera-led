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

all : build

flash : cv_flash
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
