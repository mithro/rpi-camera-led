# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate hardware/rpi-camera-led.kicad_sch.

The schematic is built programmatically: symbols are copied from the local
KiCad 9 symbol libraries, instances are placed on a grid, and every electrical
connection is made with a short wire stub plus a global label at each pin.
Run gen_schematic.py, then check_schematic.py to verify ERC and the netlist.

Usage (from the repository root):
    uv run hardware/tools/gen_schematic.py
"""

import re
import uuid
from pathlib import Path

KICAD_SYMS = Path("/snap/kicad/current/usr/share/kicad/symbols")
OUT = Path(__file__).resolve().parent.parent / "rpi-camera-led.kicad_sch"
PROJECT = "rpi-camera-led"
ROOT_UUID = "e63e39d7-6ac0-4ffd-8d43-caa4c50fe2f6"

SYMBOLS = {  # lib_id -> (library file, symbol name)
    "Device:R": ("Device.kicad_sym", "R"),
    "Device:C": ("Device.kicad_sym", "C"),
    "Device:LED": ("Device.kicad_sym", "LED"),
    "Device:Q_Photo_NPN": ("Device.kicad_sym", "Q_Photo_NPN"),
    "Transistor_FET:Q_NMOS_GSD": ("Transistor_FET.kicad_sym", "Q_NMOS_GSD"),
    "Connector_Generic:Conn_01x15": ("Connector_Generic.kicad_sym", "Conn_01x15"),
    "Connector_Generic:Conn_01x04": ("Connector_Generic.kicad_sym", "Conn_01x04"),
    "Connector_Generic:Conn_01x03": ("Connector_Generic.kicad_sym", "Conn_01x03"),
    "MCU_WCH_RiscV:CH32V003AxMx": ("MCU_WCH_RiscV.kicad_sym", "CH32V003AxMx"),
    "power:PWR_FLAG": ("power.kicad_sym", "PWR_FLAG"),
}

STUB = 3.81  # wire stub length from pin to its global label


def extract_symbol(lib_file, name):
    text = (KICAD_SYMS / lib_file).read_text()
    i = text.index(f'(symbol "{name}"')
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    raise ValueError(name)


def pin_info(block):
    """pin number -> (x, y, orientation deg) in symbol coordinates."""
    pins = {}
    for m in re.finditer(
        r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]+)"',
        block,
        re.S,
    ):
        x, y, rot, num = m.groups()
        pins[num] = (float(x), float(y), int(rot))
    return pins


LIB_BLOCKS = {}
LIB_PINS = {}
for lib_id, (lib_file, name) in SYMBOLS.items():
    block = extract_symbol(lib_file, name)
    assert "(extends" not in block.split("\n")[0], f"{name} extends another symbol"
    LIB_BLOCKS[lib_id] = block.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)
    LIB_PINS[lib_id] = pin_info(block)


def u():
    return str(uuid.uuid4())


body = []
symbol_instances = []


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def place(lib_id, ref, value, x, y, nets, footprint="", dnp=False, extra_props=(),
          ref_at=(2, -6), value_at=(2, 6)):
    """Place a symbol at (x, y) rotation 0; nets maps pin number -> net label
    (or None for an explicit no-connect)."""
    # Snap the placement to KiCad's 1.27mm connection grid so every pin
    # (whose library offsets are 1.27 multiples) lands on-grid.
    x = round(x / 1.27) * 1.27
    y = round(y / 1.27) * 1.27
    sid = u()
    pins = LIB_PINS[lib_id]
    prop_fmt = (
        '    (property "{n}" "{v}" (at {x} {y} 0)'
        " (effects (font (size 1.27 1.27)) {h}))"
    )
    props = [
        prop_fmt.format(n="Reference", v=esc(ref),
                        x=round(x + ref_at[0], 2), y=round(y + ref_at[1], 2), h=""),
        prop_fmt.format(n="Value", v=esc(value),
                        x=round(x + value_at[0], 2), y=round(y + value_at[1], 2), h=""),
        prop_fmt.format(n="Footprint", v=esc(footprint), x=x, y=y, h="(hide yes)"),
        prop_fmt.format(n="Datasheet", v="", x=x, y=y, h="(hide yes)"),
        prop_fmt.format(n="Description", v="", x=x, y=y, h="(hide yes)"),
    ]
    for name, val in extra_props:
        props.append(prop_fmt.format(n=esc(name), v=esc(val), x=x, y=y, h="(hide yes)"))
    pin_lines = "\n".join(f'    (pin "{n}" (uuid "{u()}"))' for n in pins)
    symbol_instances.append(
        f'  (symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)\n'
        f"    (exclude_from_sim no) (in_bom yes) (on_board yes)"
        f" (dnp {'yes' if dnp else 'no'})\n"
        f'    (uuid "{sid}")\n' + "\n".join(props) + "\n" + pin_lines + "\n"
        f'    (instances (project "{PROJECT}"\n'
        f'      (path "/{ROOT_UUID}" (reference "{esc(ref)}") (unit 1))))\n'
        f"  )"
    )
    # Wire stubs + global labels (or no-connects) at each pin.
    for num, net in nets.items():
        px, py, prot = pins[num]
        # schematic y axis is inverted vs the symbol editor's
        ax, ay = round(x + px, 2), round(y - py, 2)
        if net is None:
            body.append(f'  (no_connect (at {ax} {ay}) (uuid "{u()}"))')
            continue
        # Pin rotation gives the direction the pin extends toward the body
        # (symbol space, y up): 0=+x, 90=+y, 180=-x, 270=-y. The stub goes the
        # opposite way (outward), mapped into schematic space (y down).
        dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[prot]
        ex, ey = round(ax + dx * STUB, 2), round(ay + dy * STUB, 2)
        body.append(
            f"  (wire (pts (xy {ax} {ay}) (xy {ex} {ey}))"
            f' (stroke (width 0) (type default)) (uuid "{u()}"))'
        )
        angle = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[(dx, dy)]
        # justify left extends the text up/left of the anchor; right extends it
        # down/right (empirically checked with KiCad 9).
        just = {180: "right", 0: "left", 270: "right", 90: "left"}[angle]
        body.append(
            f'  (global_label "{esc(net)}" (shape bidirectional)'
            f" (at {ex} {ey} {angle}) (fields_autoplaced yes)"
            f" (effects (font (size 1.27 1.27)) (justify {just}))"
            f' (uuid "{u()}"))'
        )


def text(s, x, y, size=1.27):
    body.append(
        f'  (text "{esc(s)}" (exclude_from_sim no) (at {x} {y} 0)'
        f' (effects (font (size {size} {size})) (justify left bottom))'
        f' (uuid "{u()}"))'
    )


# --- Connectors -------------------------------------------------------------
FFC_FP = "Connector_FFC-FPC:JUSHUO_AFA07-S15FCA-00_1x15-1MP_P1.0mm_Horizontal"
CAM_NETS = {
    "1": "GND", "2": "CAM_D0_N", "3": "CAM_D0_P", "4": "GND",
    "5": "CAM_D1_N", "6": "CAM_D1_P", "7": "GND",
    "8": "CAM_CK_N", "9": "CAM_CK_P", "10": "GND",
    "13": "SCL", "14": "SDA", "15": "3V3",
}
place(
    "Connector_Generic:Conn_01x15", "J1", "FFC 15P 1.0mm (to Raspberry Pi)",
    45, 80, {**CAM_NETS, "11": "PI_IO0", "12": "PI_IO1"}, footprint=FFC_FP,
    value_at=(-14, 25),
    extra_props=[("MPN", "JUSHUO AFA07-S15FCA-00 / Amphenol SFW15R-1STE1LF")],
)
place(
    "Connector_Generic:Conn_01x15", "J2", "FFC 15P 1.0mm (to camera)",
    260, 80, {**CAM_NETS, "11": "CAM_IO0", "12": "CAM_IO1"}, footprint=FFC_FP,
    value_at=(-8, 28),
    extra_props=[("MPN", "JUSHUO AFA07-S15FCA-00 / Amphenol SFW15R-1STE1LF")],
)
place(
    "Connector_Generic:Conn_01x04", "J3", "Qwiic (JST SH 1.0mm)",
    45, 140, {"1": "GND", "2": "3V3", "3": "SDA", "4": "SCL"}, value_at=(-8, 10),
    footprint="Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
    extra_props=[("MPN", "JST SM04B-SRSS-TB or SH1.0-4P clone")],
)
place(
    "Connector_Generic:Conn_01x03", "J4", "SWD program header 2.54mm",
    45, 170, {"1": "3V3", "2": "SWIO", "3": "GND"}, value_at=(-8, 8),
    footprint="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
)

# --- MCU --------------------------------------------------------------------
# Pin numbers per the WCH CH32V003 datasheet V1.8 table 2-1 (SOP16 column).
# Unlike the SOP-8 part no pin bonds two ports, so PD1 carries SWIO alone and
# PC3 (TIM1 CH3, a true output rather than the complementary CH3N) drives the
# LED gate.  Spare pins take explicit no-connects so ERC stays clean.
place(
    "MCU_WCH_RiscV:CH32V003AxMx", "U1", "CH32V003A4M6",
    150, 60,
    {"1": "SDA", "2": "SCL", "3": "LED_PWM", "4": "LIGHT_SENSE",
     "5": None, "6": None, "7": "SWIO", "8": None, "9": None,
     "10": "CAM_IO0", "11": None, "12": None, "13": "CAM_IO1",
     "14": "GND", "15": "3V3", "16": None},
    ref_at=(-4, -16), value_at=(-14, 20),
    footprint="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
    extra_props=[("MPN", "WCH CH32V003A4M6 (LCSC C5346357)")],
)

# --- Decoupling -------------------------------------------------------------
place("Device:C", "C1", "100nF", 120, 95, {"1": "3V3", "2": "GND"},
      footprint="Capacitor_SMD:C_0402_1005Metric")
place("Device:C", "C2", "1uF", 135, 95, {"1": "3V3", "2": "GND"},
      footprint="Capacitor_SMD:C_0402_1005Metric")

# --- I2C pull-ups -----------------------------------------------------------
place("Device:R", "R1", "4.7k", 160, 95, {"1": "3V3", "2": "SDA"},
      footprint="Resistor_SMD:R_0402_1005Metric")
place("Device:R", "R2", "4.7k", 172, 95, {"1": "3V3", "2": "SCL"},
      footprint="Resistor_SMD:R_0402_1005Metric")

# --- GPIO couplers: pass-through, Pi-state sensing, and CH32 override -------
place("Device:R", "R6", "10k", 152, 130, {"1": "PI_IO0", "2": "CAM_IO0"},
      footprint="Resistor_SMD:R_0402_1005Metric")
place("Device:R", "R7", "10k", 164, 130, {"1": "PI_IO1", "2": "CAM_IO1"},
      footprint="Resistor_SMD:R_0402_1005Metric")

# --- Illumination LEDs ------------------------------------------------------
place("Device:R", "R3", "10R", 200, 95, {"1": "3V3", "2": "LED1_A"},
      footprint="Resistor_SMD:R_0603_1608Metric")
place("Device:R", "R4", "10R", 236, 95, {"1": "3V3", "2": "LED2_A"},
      footprint="Resistor_SMD:R_0603_1608Metric")
place("Device:LED", "D1", "White LED", 198, 115, {"2": "LED1_A", "1": "LED_SW"},
      ref_at=(-2, -4), value_at=(-6, 5),
      footprint="LED_SMD:LED_0805_2012Metric",
      extra_props=[("MPN", "White 0805/2835, e.g. Hongli/NationStar")])
place("Device:LED", "D2", "White LED", 236, 115, {"2": "LED2_A", "1": "LED_SW"},
      ref_at=(-2, -4), value_at=(-6, 5),
      footprint="LED_SMD:LED_0805_2012Metric",
      extra_props=[("MPN", "White 0805/2835, e.g. Hongli/NationStar")])
place("Transistor_FET:Q_NMOS_GSD", "Q1", "AO3400A", 207, 140,
      {"1": "LED_GATE", "2": "GND", "3": "LED_SW"},
      ref_at=(7, -4), value_at=(7, 2),
      footprint="Package_TO_SOT_SMD:SOT-23")
place("Device:R", "R5", "100R", 178, 138, {"1": "LED_PWM", "2": "LED_GATE"},
      footprint="Resistor_SMD:R_0402_1005Metric")
place("Device:R", "R8", "10k", 168, 166, {"1": "LED_GATE", "2": "GND"},
      footprint="Resistor_SMD:R_0402_1005Metric")

# --- Light sensor -----------------------------------------------------------
place("Device:Q_Photo_NPN", "Q2", "Phototransistor", 100, 140,
      {"1": "3V3", "2": "LIGHT_SENSE"},
      ref_at=(7, -4), value_at=(7, 2),
      footprint="LED_SMD:LED_0805_2012Metric",
      extra_props=[("MPN", "e.g. Everlight PT17-21C/L41/TR8")])
place("Device:R", "R9", "47k", 100, 166, {"1": "LIGHT_SENSE", "2": "GND"},
      ref_at=(6, -6), value_at=(6, 4),
      footprint="Resistor_SMD:R_0402_1005Metric")

# --- Power flags ------------------------------------------------------------
place("power:PWR_FLAG", "#FLG01", "PWR_FLAG", 75, 180, {"1": "3V3"},
      ref_at=(0, -9), value_at=(0, -6))
place("power:PWR_FLAG", "#FLG02", "PWR_FLAG", 88, 180, {"1": "GND"},
      ref_at=(0, -9), value_at=(0, -6))

# --- Notes ------------------------------------------------------------------
text("RPi Camera LED interposer: sits between a Raspberry Pi and its camera.\n"
     "MIPI lanes, I2C, GND and 3V3 pass straight through J1 -> J2.\n"
     "U1 (I2C slave on the camera bus) drives the camera GPIO pins 11/12,\n"
     "PWM-drives the illumination LEDs and reads ambient light on its ADC.",
     20, 30, 2.0)
text("R6/R7 couple the Pi's CAM_IO pins to the camera pins/U1: with U1\n"
     "high-Z (or unpopulated) the Pi's state passes through and U1 can read\n"
     "it; when U1 drives, it overrides the Pi through the 10k.",
     108, 164)
text("SOP-16 bonds no two ports to one pin, so PD1/SWIO is programming only\n"
     "and PC3/T1CH3 drives the LED gate: no LED flicker while flashing firmware.\n"
     "PC6, PC7, PD4, PD5, PD7/NRST, PA1 and PC0 are spare.",
     95, 193)
text("LED current is set by R3/R4 against the 3V3 rail (about 30-40mA each\n"
     "with Vf=2.9V). Total draw comes from the Pi camera 3V3 supply - keep\n"
     "the duty/current within the Pi's camera connector budget.",
     183, 32)
text("All parts chosen for JLCPCB / NextPCB Rev0 assembly; see\n"
     "research/*.md for availability and pricing (checked 2026-09-01).",
     20, 195)

# --- Assemble ---------------------------------------------------------------
sheet = (
    '(kicad_sch (version 20250114) (generator "gen_schematic.py")'
    ' (generator_version "9.0")\n'
    f'  (uuid "{ROOT_UUID}")\n'
    '  (paper "A4" portrait)\n'
    "  (title_block\n"
    '    (title "RPi Camera LED interposer")\n'
    '    (date "2026-09-01")\n'
    '    (rev "A")\n'
    '    (comment 1 "CH32V003A4M6 camera GPIO / illumination / light sensor")\n'
    "  )\n"
    "  (lib_symbols\n"
    + "\n".join(LIB_BLOCKS.values())
    + "\n  )\n"
    + "\n".join(body)
    + "\n"
    + "\n".join(symbol_instances)
    + "\n"
    f'  (sheet_instances (path "/" (page "1")))\n'
    ")\n"
)
# A4 landscape is the default orientation ("paper A4" without portrait).
sheet = sheet.replace('(paper "A4" portrait)', '(paper "A4")')
OUT.write_text(sheet)
print(f"wrote {OUT} ({len(sheet)} chars)")
