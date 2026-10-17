# Camera/interposer fit model

`generate_camera_assembly.FCMacro` imports the KiCad substrate STEP, populated
component groups, and the user-supplied Raspberry Pi Camera v3 model.
`render_assembly.py` imports the resulting STL parts in Blender and writes top,
stackup, translucent fit-check, and underside renders to `tmp/cad/`.

The original 3MF and its converted STEP live in `hardware/cad/models/`.
Regenerate the faceted STEP from the project copy with:

```powershell
& "C:\Program Files\FreeCAD 0.19\bin\FreeCADCmd.exe" -c hardware\cad\convert_camera_3mf.FCMacro
```

The conversion sews the 3MF facets into a closed solid before STEP export.
The result is a faceted solid, not an editable native CAD model.

From the repository root, regenerate the substrate STEP and run:

```powershell
kicad-cli pcb export step --board-only -o tmp/manufacturing/rpi-camera-led-board.step hardware/rpi-camera-led.kicad_pcb
& "C:\Program Files\FreeCAD 0.19\bin\FreeCADCmd.exe" -c hardware\cad\generate_camera_assembly.FCMacro
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python hardware\cad\render_assembly.py
```

The macro exports component groups (connectors, MCU, LEDs, sensor, MOSFET, and
passives) with both KiCad 9 and 10 model-directory variables. It locates
`kicad-cli` through the project helper and searches standard KiCad model paths;
set `KICAD9_3DMODEL_DIR` or `KICAD10_3DMODEL_DIR` to override them.

The supplied 3MF is titled `Raspberry Pi Camera v3`; its mesh measures
25 x 24 mm in plan and places the lens axis at its XY origin. Its mounting
holes appear at 20 x 12.5 mm pitch, with the pattern center 6.25 mm from the
lens axis. The assembly keeps the optical axis on the interposer aperture
center and places the four holes at the model's coordinates, matching its
20 x 12.5 mm pitch. The hole pattern is consequently offset 6.25 mm from the
optical axis; the relocated pattern and shifted LED row are included in the
routed PCB. The fit-check is model-based, not physical verification; confirm
the camera's exact revision and mounting-hole dimensions before fabrication.
The Raspberry Pi FFC path remains illustrative.
