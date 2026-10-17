"""Render the FreeCAD camera/interposer assembly with Blender 5.x."""

from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY = ROOT / "tmp" / "cad"
OUTPUT = ASSEMBLY / "rpi-camera-led-assembly"


def material(name, color, metallic=0.0, roughness=0.4, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if alpha < 1.0:
        mat.surface_render_method = "BLENDED"
        bsdf.inputs["Alpha"].default_value = alpha
    return mat


materials = {
    "Interposer": material("Interposer solder mask", (0.07, 0.28, 0.42)),
    "ComponentsConnectors": material("Connector housings", (0.82, 0.79, 0.67)),
    "ComponentsIC": material("Metering MCU package", (0.07, 0.08, 0.1)),
    "ComponentsLEDs": material("LED packages", (0.9, 0.88, 0.76)),
    "ComponentsSensor": material("Phototransistor package", (0.16, 0.3, 0.38), roughness=0.2),
    "ComponentsMOSFET": material("MOSFET package", (0.1, 0.12, 0.14)),
    "ComponentsPassives": material("Passive component bodies", (0.7, 0.66, 0.53)),
    "CameraModule": material("Camera module PCB", (0.1, 0.24, 0.45)),
    "AutofocusActuator": material("Autofocus actuator", (0.19, 0.2, 0.23), roughness=0.3),
    "LensHolder": material("Autofocus lens barrel", (0.025, 0.03, 0.045), roughness=0.2),
    "LensGlass": material("Autofocus lens glass", (0.04, 0.16, 0.26), metallic=0.4, roughness=0.12),
    "CameraFFCConnector": material("Camera FFC connector", (0.79, 0.76, 0.65)),
    "Spacer": material("Mounting standoffs", (0.38, 0.42, 0.48), metallic=0.75),
    "FFC": material("Flexible ribbon cables", (0.67, 0.48, 0.21), metallic=0.15),
}

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

for stl in sorted(ASSEMBLY.glob("*.stl")):
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(stl))
    else:
        bpy.ops.import_mesh.stl(filepath=str(stl))
    imported = bpy.context.selected_objects
    if not imported:
        raise RuntimeError(f"Blender imported no objects from {stl.name}")
    for obj in imported:
        obj.name = stl.stem
        if obj.name.startswith("Spacer"):
            mat = materials["Spacer"]
        elif obj.name in ("CameraFFC", "PiFFC"):
            mat = materials["FFC"]
        else:
            mat = materials.get(obj.name, materials["FFC"])
        obj.data.materials.clear()
        obj.data.materials.append(mat)

floor_mat = material("Matte neutral floor", (0.12, 0.14, 0.17), roughness=0.82)
bpy.ops.mesh.primitive_plane_add(size=180, location=(32.5, -31.9, -8.3))
floor = bpy.context.object
floor.name = "RenderFloor"
floor.data.materials.append(floor_mat)

world = bpy.data.worlds.new("Studio")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.15, 0.2, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7

def add_area(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = location
    direction = Vector((32.5, -31.9, -1.5)) - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


add_area("Key", (10, 20, 80), 22000, 55, (1.0, 0.84, 0.68))
add_area("Fill", (78, -65, 48), 14000, 45, (0.64, 0.77, 1.0))
add_area("Rim", (-25, -15, 35), 10000, 35, (0.8, 0.9, 1.0))
add_area("BottomKey", (10, -20, -42), 18000, 55, (1.0, 0.86, 0.72))
add_area("BottomFill", (65, -80, -35), 14000, 45, (0.68, 0.8, 1.0))

camera_data = bpy.data.cameras.new("AssemblyCamera")
camera = bpy.data.objects.new("AssemblyCamera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 86
camera.location = (95, 35, 65)
target = Vector((32.5, -31.9, -1.5))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.render.filepath = str(OUTPUT.with_name(OUTPUT.name + "-top.png"))
scene.camera.data.lens = 50
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUTPUT.with_name(OUTPUT.name + "-top.png"))
bpy.ops.render.render(write_still=True)

floor.hide_render = True
camera.location = (90, -105, 24)
target = Vector((32.5, -31.9, -1.5))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.ortho_scale = 90
scene.render.filepath = str(OUTPUT.with_name(OUTPUT.name + "-stackup.png"))
bpy.ops.render.render(write_still=True)

interposer = bpy.data.objects.get("Interposer")
if interposer is None:
    raise RuntimeError("Interposer board mesh is missing")
fit_material = material("Translucent interposer for camera fit check", (0.07, 0.28, 0.42), alpha=0.22)
interposer.data.materials.clear()
interposer.data.materials.append(fit_material)
camera.location = (32.5, -31.9, 145)
target = Vector((32.5, -31.9, -2.0))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.ortho_scale = 58
scene.render.filepath = str(OUTPUT.with_name(OUTPUT.name + "-raspberry-pi-camera-v3-fit-check.png"))
bpy.ops.render.render(write_still=True)

camera.location = (70, -90, -45)
target = Vector((32.5, -31.9, -2.5))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.ortho_scale = 90
scene.render.filepath = str(OUTPUT.with_name(OUTPUT.name + "-underside.png"))
bpy.ops.render.render(write_still=True)
