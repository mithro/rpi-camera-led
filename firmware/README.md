# CH32V003J4M6 camera-LED controller firmware

Firmware for the CH32V003J4M6 (RISC-V, SOP-8) sitting on the Raspberry
Pi camera interposer board in this repository. It:

1. drives or tri-states the two camera-side GPIO pins,
2. reads back the two Pi-side GPIO pins (via the tri-stated passthrough),
3. can put either channel into "copy mode" (the Pi's GPIO passes
   straight through to the camera),
4. continuously samples and averages an ambient-light phototransistor,
5. drives two white illumination LEDs via hardware PWM, and
6. supports a fail-safe firmware upgrade over I2C.

Everything is controlled by a Raspberry Pi over I2C, using a plain
"8-bit register pointer, auto-incrementing" protocol compatible with
`i2c-tools` (`i2cget`/`i2cset`/`i2ctransfer`) and kernel `regmap-i2c`
drivers out of the box.

**Build status: builds clean with fully open-source tooling (see
"Build" below). Hardware status: UNTESTED. Nobody has flashed this
onto a real board or scoped a single pin -- see "What is untested"
at the end of this document.**

## Hardware

(As specified by the person who wrote this brief, verified against the
WCH datasheet.) The chip is a CH32V003J4M6 in an SOP-8 package. Several
package pins are bonded to two GPIO ports simultaneously inside the
package, which the firmware must account for:

| Package pin | Port(s)         | Net       | Notes |
|-------------|------------------|-----------|-------|
| 1           | PD6 **and** PA1  | CAM_IO0   | Drives camera GPIO 11. Also wired through a 10k (R6) to the Pi's CAM_IO0: when the CH32 pin is an input, the Pi's state passes through to the camera and is readable by the CH32; when the CH32 drives it, it overrides the Pi (0.33mA through the 10k). |
| 3           | PA2              | CAM_IO1   | Same scheme via R7 (10k) to the Pi's CAM_IO1. |
| 5           | PC1              | I2C1_SDA  | CH32 is an I2C **slave** on the Pi camera bus (100-400kHz), shared with the camera sensor (0x10/0x1A/0x36) and EEPROMs (0x50/0x54). |
| 6           | PC2              | I2C1_SCL  | |
| 7           | PC4              | ADC A2    | Phototransistor, 47k to GND; more light = higher voltage. |
| 8           | PD1, PD4, PD5    | LED gate  | PD1 drives an N-MOSFET gate (100R series, 10k pulldown) switching two white LEDs, via TIM1 channel 3 complementary output (T1CH3N). PD1/SWIO is also the programming pin -- LEDs flicker during flashing, by design. |

Because pins 1 and 8 are bonded to more than one port, the firmware
configures the *unused* half of each bonded pin as a floating input
for its entire lifetime, so it never fights the pin it's bonded to:
PA1 (pin 1) and PD4/PD5 (pin 8) are always `GPIO_CFGLR_IN_FLOAT`. This
is also the chip's power-on-reset default for every GPIO, so the
bootloader (which never touches these pins) is safe by construction,
and the app explicitly re-asserts it at startup as a defensive measure
(`app/app.c`, `main()`).

I2C slave address: **0x42** (`I2C_SLAVE_ADDR` in `common/layout.h`),
chosen to avoid the camera (0x10/0x1A/0x36) and EEPROMs (0x50/0x54)
already on the bus.

## Architecture

16KiB of flash is split into two independently-linked images:

```
0x0000 - 0x0FFF   bootloader   (4KiB)   -- always runs first
0x1000 - 0x3FFF   application  (12KiB)  -- code + a 16-byte trailer
```

2KiB of SRAM is shared: the first 16 bytes are reserved for a
cross-reset handshake word (see "Upgrade protocol" below) that is
**not** zeroed by C runtime startup, so it can carry a value across a
warm reset; the rest is split identically by both linker scripts
(`bootloader/bootloader.ld`, `app/app.ld`) but is otherwise fully
available to whichever image is currently running -- the two images
are never active at the same time, so there's no need to partition RAM
between them beyond that one shared word.

The bootloader **always** runs first (the chip always starts executing
at flash address 0 after reset). On every boot it:

1. Computes the application's CRC32 and compares it to the CRC32
   stored in the application's own trailer.
2. If valid **and** no upgrade was requested, jumps straight to the
   application (a few hundred microseconds of overhead).
3. Otherwise, stays resident and serves the I2C bootloader protocol
   until a host either fixes the app and asks it to run, or the app
   itself explicitly asks to be interrupted for an upgrade.

The bootloader **never** erases or programs any flash address outside
the 12KiB application region -- see `program_page()` in
`bootloader/bootloader.c`, which bounds-checks every page index
against `APP_NUM_PAGES` before touching the flash controller. There is
no code path, valid or malformed I2C command, that can make it write
to its own 4KiB.

### Why two separately-linked images "just work"

Each image is built by ch32fun's normal startup code (`handle_reset`
in the submodule's `ch32fun.c`), which sets `mtvec` to that image's
*own* `InterruptVector` symbol (`la a3, InterruptVector; ori a3,a3,3;
csrw mtvec,a3`) and jumps into that image's own `main()`. Since the
bootloader and app are linked with different `FLASH` origins
(`bootloader.ld`: `0x00000000`; `app.ld`: `0x00001000`), this happens
automatically -- the bootloader does not need to (and does not)
manually relocate the app's vector table. "Jumping to the app" is
therefore just a plain function-pointer call to `APP_FLASH_BASE`
(`0x00001000`), which lands on the app's own reset vector and the app
takes it from there (`jump_to_app()` in `bootloader.c`).

Flash reads/writes/erases use the *physical* address
(`APP_FLASH_PHYS_BASE = 0x08001000`), matching how
`ch32v003fun/examples/flashtest/flashtest.c` uses the flash controller
-- the CPU's normal code-fetch/read path uses the *aliased* address
(`APP_FLASH_BASE = 0x00001000`, the boot-remapped alias flash sits at
after reset) for execution. Both addresses read the same bytes; only
the *jump* target needs to be the aliased one (to match what `mtvec`/
`la` compute), and only the flash-controller `FLASH->ADDR`/buffer
writes need to be the physical one (as demonstrated by the stock
`flashtest.c` example).

## Register map (application mode)

I2C slave address `0x42`. All registers are 8-bit-addressed with
auto-increment (a write's first byte sets the pointer; further bytes
in the same write auto-increment it; a read serves from the pointer
and also auto-increments) -- see `common/i2c_slave.h` (vendored,
MIT-licensed, from the ch32v003fun submodule's `examples/i2c_slave`).
This is the same "dumb register file" shape `i2c-tools` and kernel
`regmap-i2c` drivers expect.

| Reg  | Name       | R/W | Description |
|------|------------|-----|-------------|
| 0x00 | WHO_AM_I   | RO  | `0xC3` in application mode, `0xB1` in bootloader mode -- read this first to know which one you're talking to. |
| 0x01 | FW_VERSION | RO  | Application firmware version (currently 1). |
| 0x02 | CTRL       | RW  | bit0/bit1 = copy-mode enable, channel 0/1. |
| 0x03 | GPIO_OUT   | RW  | bit0/bit1 = driven output level, channel 0/1 (only takes effect if OE=1 and copy-mode is off for that channel). |
| 0x04 | GPIO_OE    | RW  | bit0/bit1 = 1: drive the pin per GPIO_OUT, 0: tri-state (input). Ignored (forced to tri-state) while copy-mode is enabled for that channel. |
| 0x05 | GPIO_IN    | RO  | bit0/bit1 = live pin level, channel 0/1. When tri-stated (copy mode, or OE=0) this is the Pi's passed-through state; when driven (OE=1, copy mode off) this reads back the value we're driving. |
| 0x06 | LED        | RW  | LED brightness, 0-255, hardware PWM (~1kHz). |
| 0x07 | (reserved) | -   | Reads as 0. |
| 0x08-0x09 | LIGHT | RO  | Illumination, little-endian 16-bit, exponentially averaged (~8-sample time constant at ~100Hz sampling). Raw ADC is 10-bit, so the value ranges 0-1023, not the full 16-bit range. |
| 0x7F | BOOT       | WO  | Write `0xB0` to ask the running app to reset into the bootloader for a firmware upgrade. |

**Copy mode precedence:** if `CTRL` bit *n* is set, channel *n* is
**always** tri-stated regardless of `GPIO_OE` bit *n* -- that tri-state
*is* the passthrough (the Pi's own driver, through the 10k resistor,
is what reaches the camera; the CH32 just gets out of the way and
reports what it reads back on `GPIO_IN`).

## Register map (bootloader mode)

Same I2C address (`0x42`) and same register-pointer/auto-increment
protocol, exposed only while the bootloader is resident. `WHO_AM_I`
reads `0xB1` here (vs `0xC3` in app mode) so a host can always tell
which firmware it's talking to just by reading register 0.

| Reg       | Name           | R/W | Description |
|-----------|----------------|-----|-------------|
| 0x00      | WHO_AM_I       | RO  | `0xB1`. |
| 0x01      | BL_VERSION     | RO  | Bootloader version (currently 1). |
| 0x02      | STATUS         | RO  | bit0 BUSY, bit1 OK (last op), bit2 ERR (last op), bit3 APP_VALID (result of the most recent CRC32 check). |
| 0x03      | CMD            | WO  | Write a command byte: `0x01` PROGRAM_PAGE, `0x02` VERIFY_APP, `0x03` RUN_APP. |
| 0x04      | PAGE_INDEX     | RW  | Page number (0-191) within the 12KiB application region, for the next PROGRAM_PAGE. |
| 0x05-0x06 | PAGE_CSUM      | RW  | Little-endian CRC16/CCITT-FALSE of the 64-byte PAGE_BUF, checked by the bootloader before it touches flash. |
| 0x07      | (reserved)     | -   | Reads as 0. |
| 0x08-0x47 | PAGE_BUF       | RW  | 64-byte page data buffer (the CH32V003's flash erase granularity). |
| 0x48-0x4B | APP_CRC32      | RO  | Little-endian, the CRC32 computed by the most recent VERIFY_APP (or the automatic check at bootloader entry). |
| 0x4C-0x4F | APP_SIZE       | RO  | Little-endian, `app_header_t.app_used_size` as last read from flash (always 12288 for images built by this repo's tooling). |

### `PROGRAM_PAGE` semantics

Writing `0x01` to `CMD` erases, programs, and read-back-verifies
*exactly one* 64-byte page of the application region at `PAGE_INDEX`,
from `PAGE_BUF`, but **only if** the CRC16 the bootloader computes over
`PAGE_BUF` matches `PAGE_CSUM` -- a mismatch aborts before touching
flash and sets the ERR bit. This work happens in the bootloader's main
loop (not the I2C interrupt handler), so it can take a few
milliseconds (flash page erase is documented elsewhere in the
ch32v003fun project as ~3ms); **a host must poll STATUS until BUSY
clears (or simply wait ~10ms) before sending the next command** --
see `_wait_not_busy()` / `_program_page()` in `host/rpi_camera_led.py`.
`PAGE_INDEX` is always bounds-checked against the 192-page application
region before any flash access, so a confused or malicious host cannot
make the bootloader touch its own 4KiB.

## Upgrade protocol and its fail-safety argument

The application's flash image ends in a 16-byte trailer
(`app_header_t`, `common/app_header.h`) occupying exactly the last 16
bytes of the last (192nd) page of the application region:

```c
typedef struct {
    uint32_t magic;          // must equal 0xCAFEB007
    uint32_t app_used_size;  // bytes covered by crc32 below, from the
                              // start of the app region (always 12288
                              // for images this repo's tooling builds)
    uint32_t app_crc32;      // CRC32 (zlib/CRC-32/ISO-HDLC variant) of
                              // app_used_size bytes, computed with THIS
                              // FIELD treated as zero
    uint32_t reserved;       // must be 0
} app_header_t;
```

Because the trailer sits at a fixed, compile-time-known address
(`APP_HEADER_ADDR = 0x00003FF0`) regardless of how big the actual
compiled code is, the bootloader never needs to trust anything about
the application's own build beyond this one fixed struct.

The full upgrade sequence, driven by `host/rpi_camera_led.py upgrade`:

1. If the device is currently running the app, write `0xB0` to
   `REG_BOOT`. The app stashes a magic value in the shared NOINIT RAM
   word and triggers a full system reset (`PFIC->SCTLR = 1<<31`). The
   bootloader (which always runs first) sees the magic value, clears
   it, and stays resident regardless of whether the current app's CRC32
   is valid.
2. For each of the 192 pages: write `PAGE_INDEX`/`PAGE_CSUM`/`PAGE_BUF`
   in one I2C transaction, then write `CMD = PROGRAM_PAGE` in a second,
   then poll `STATUS` until not-BUSY and check OK.
3. Write `CMD = VERIFY_APP`; poll; check `APP_VALID`.
4. Write `CMD = RUN_APP`; the bootloader jumps to the (now verified)
   app.

**Why a power cut at any point in this sequence is recoverable:**

- *Before any page is written*, the flash is whatever it was before --
  either the previous (working) app, or already-invalid flash from an
  earlier interrupted attempt. Either way, the CRC32 check at the next
  boot reflects reality.
- *During any single page's erase+program*, the flash controller
  (per `ch32v003fun/examples/flashtest`) can leave that specific page
  in an indeterminate state (partially erased, partially programmed)
  if power is cut mid-operation. This is **not** made atomic by this
  firmware -- it can't be, on this hardware, without a second flash
  bank to hold a journal, which a 16KiB part doesn't have. What *is*
  guaranteed is that the CRC32 check covers the **entire** 12KiB
  region, so **any** single corrupted page (this one, or the one
  holding the header trailer itself) makes the whole-image CRC32
  mismatch on the next boot, and the bootloader falls back to staying
  resident rather than running a partially-written image. The
  in-progress page write is bounds-checked to the app region the whole
  time, so even a power cut mid-erase can never touch the bootloader's
  own 4KiB.
- *Between pages*, or *after the last page but before VERIFY_APP/
  RUN_APP*, the trailer's CRC32 still describes whatever combination of
  old and new page contents happens to be in flash at that instant,
  which (overwhelmingly likely) does not match -- same fallback.
- *A power cut during RUN_APP itself* just means the reset happens
  before the jump instead of after; the bootloader re-runs its CRC32
  check from scratch on the next boot regardless.

In short: **the fail-safety guarantee rests entirely on the CRC32
check being cheap, unconditional, and run on every single boot before
anything else** -- not on any single I2C transaction being atomic. The
cross-reset NOINIT handshake word (step 1 above) is *not* part of this
guarantee; it only affects whether the bootloader stays resident when
the CRC32 *is* valid (letting an intentional re-upgrade interrupt a
working app). Concretely: SRAM content after a genuine cold power-on
is not architecturally guaranteed to be any particular value, so this
firmware never relies on the handshake word being zero/absent after a
real power loss -- it only ever matters when the CRC32 is already
valid, and reading it as (spuriously) "enter bootloader" in that case
just means an extra unnecessary stay-in-bootloader, never an unsafe
boot into a bad image.

**What this cannot rule out, honestly:** CRC32 is not a cryptographic
checksum. A pathological, exactly-crafted flash corruption pattern
could in principle produce a wrong image whose CRC32 happens to match
its own (also corrupted) stored CRC32 field. Against the kind of
corruption that a power loss during a page erase/program actually
produces (a page left all-0xFF, all-0x00, or a mix of old/new 32-bit
words), this is not a realistic failure mode, but it is not
mathematically impossible, and this document says so plainly rather
than overclaiming.

The I2C-transport-level `PAGE_CSUM` (CRC16) is a **separate**, weaker
check that only protects a single page transfer against I2C bus
corruption *before* it reaches flash -- it plays no role in the
boot-time safety argument above, which is CRC32-only.

## Build

Requires `riscv64-unknown-elf-gcc` (Debian/Ubuntu package
`gcc-riscv64-unknown-elf`) and `uv` (for the trailer-patching Python
step). Both bootloader and app are built with
`-march=rv32ec -mabi=ilp32e`, matching what `ch32v003fun`'s own
`ch32fun.mk` selects for `TARGET_MCU=CH32V003`.

```sh
git submodule update --init firmware/ch32v003fun   # if not already checked out
cd firmware/bootloader && make build
cd ../app && make build
```

Each `Makefile` enforces its flash budget at build time (`checksize`
target) in addition to the linker's own `--print-memory-usage` report,
using `objcopy -O ihex`/`-O binary` for the standard `.elf`/`.bin`/
`.hex` outputs.

Measured sizes (this repository, current sources):

```
Bootloader:  2196 / 4096  bytes flash (53.6%),  132 / 2032 bytes RAM
App:         1992 / 12272 bytes flash (16.2%),  184 / 2032 bytes RAM
```

(App flash budget is 12272, not 12288 -- the linker script reserves
the last 16 bytes for the trailer that `app/make_trailer.py` patches
in after linking, so the *build itself* fails loudly if application
code would collide with the trailer, rather than silently producing a
corrupt image.)

## Flashing

This firmware has not been flashed to real hardware (see "What is
untested" below). `ch32fun.mk` provides a `cv_flash` target
(`make flash` in either `bootloader/` or `app/`) that uses
`minichlink` (built from the `ch32v003fun` submodule, also fully
open-source) over a WCH-LinkE-compatible SWD programmer connected to
the shared SWIO/PD1 pin. Because PD1 is also the LED PWM pin, the LEDs
will flicker while flashing the app image -- this is expected and
harmless.

The bootloader only needs to be flashed once (via SWD); subsequent
application updates go over I2C via `host/rpi_camera_led.py upgrade`,
which never touches the bootloader's own flash region.

## Host tool

`host/rpi_camera_led.py` (run with `uv run rpi_camera_led.py ...`,
stdlib-only, no packages to install) talks to `/dev/i2c-N` via a small
ctypes wrapper (`host/i2c_raw.py`) around the same `I2C_RDWR` ioctl
`i2c-tools`/`smbus2` use, so it does not depend on `smbus2` at all.

```sh
uv run host/rpi_camera_led.py --bus 1 status
uv run host/rpi_camera_led.py --bus 1 set-led 128
uv run host/rpi_camera_led.py --bus 1 set-oe 0 1
uv run host/rpi_camera_led.py --bus 1 set-gpio 0 1
uv run host/rpi_camera_led.py --bus 1 set-copy 1 1
uv run host/rpi_camera_led.py --bus 1 get-light
uv run host/rpi_camera_led.py --bus 1 upgrade firmware/app/app.bin
```

`upgrade` accepts either a raw linked `app.bin` (it builds and patches
the trailer itself, using `host/app_trailer.py`) or an already-
trailered 12288-byte image (it verifies the trailer before flashing
rather than trusting it blindly).

## What is untested

**Nothing in this firmware has been run on real CH32V003J4M6 silicon,
or on any hardware at all.** Specifically untested:

- Whether the pin/peripheral configuration (GPIO alternate functions,
  ADC channel mapping, TIM1 NOREMAP CH3N routing to PD1) actually
  produces the described electrical behaviour on this specific
  package/board.
- Actual I2C bus timing and whether the bootloader staying
  unresponsive during a blocking flash page erase/program (a few
  milliseconds, per the ch32v003fun project's own documented figures
  for this flash controller) causes any real I2C master (including the
  Raspberry Pi's kernel I2C driver) to time out or misbehave, versus
  the host tool's current fixed poll/retry timing being adequate.
  It's likely the CPU (and hence the flash-page-write busy loop) is
  itself stalled while the flash controller executes a page erase or
  program -- meaning the I2C interrupt handler cannot run either, and
  the master will simply see the slave stop acknowledging for the
  duration -- but this has not been confirmed in hardware.
- Whether `SetupI2CSlave`'s clock configuration (2MHz logic clock,
  1MHz-nominal `CKCFGR`, intended for 100-400kHz bus operation per the
  library's own comments) is well matched to the actual bus speed the
  Raspberry Pi's camera I2C runs at.
- The actual flash page-erase/program timing and read-back-verify
  behaviour on this specific chip revision.
- Whether triggering `PFIC->SCTLR = 1<<31` from application code
  (used for the "enter bootloader" request) behaves as expected on
  this chip/silicon revision, and how long the I2C bus is unresponsive
  across that reset.
- The host tool's ioctl-based I2C implementation (`host/i2c_raw.py`)
  against a real Linux `i2c-dev` device node -- it has only been
  exercised against a Python-level mock of the bootloader's register
  state machine (see the git history for `firmware/host/`), which
  validates the *protocol logic* (page sequencing, checksums, mode
  transitions) but says nothing about real I2C electrical/timing
  behaviour.
- Real-world ADC noise/averaging behaviour of the phototransistor
  circuit, and whether the ~100Hz/8-sample exponential average is a
  sensible time constant for the actual sensor.
- LED PWM frequency (~1kHz) for visible flicker or EMI concerns.

Anyone bringing this up on real hardware should start with `make flash`
of the bootloader alone, verify `status` reports `mode: bootloader`
(a factory-blank chip has no valid app), then flash a minimal app and
work up from there.
