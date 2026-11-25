"""Blender scene recipe, called by working_render.py."""

import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def material(name, rgb, metallic=0, roughness=0.38):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    linear = [((v / 255 + 0.055) / 1.055) ** 2.4 for v in rgb]
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return mat


job = json.loads(Path(sys.argv[-1]).read_text())
root = Path(job["root"])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 14
scene.cycles.use_denoising = True
preferences = bpy.context.preferences.addons["cycles"].preferences
try:
    preferences.compute_device_type = "OPTIX"
    preferences.refresh_devices()
    devices = [device for device in preferences.devices if device.type == "OPTIX"]
    if devices:
        for device in preferences.devices:
            device.use = device in devices
        scene.cycles.device = "GPU"
except (RuntimeError, TypeError):
    pass
scene.world = bpy.data.worlds.new("Studio daylight")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.83, 0.85, 0.87, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
scene.view_settings.view_transform = "Khronos PBR Neutral"
scene.render.resolution_percentage = 100
scene.render.image_settings.color_mode = "RGB"
bpy.ops.object.camera_add()
camera = bpy.context.object
scene.camera = camera
camera.data.type = "ORTHO"
camera.data.clip_end = 1500
teal = material("Turquoise PLA", (0, 177, 183))
black = material("Graphite PLA", (38, 41, 43))
plate_material = teal
yellow = material("Sunflower yellow PLA", (254, 198, 1))
silver = material("Zinc plated steel", (185, 194, 201), 0.86, 0.26)
gold = material("Yellow plated steel", (193, 151, 73), 0.8, 0.31)
wood = material("Timber backing", (184, 144, 100), 0, 0.63)
paper = material("Warm white", (246, 244, 238))
bpy.ops.mesh.primitive_plane_add(size=2000)
floor = bpy.context.object
floor.data.materials.append(paper)
for position, power, size in [((-50, -55, 90), 95000, 65), ((65, 35, 72), 125000, 55), ((5, -70, 24), 35000, 50)]:
    bpy.ops.object.light_add(type="AREA", location=position)
    light = bpy.context.object
    light.data.energy = power
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()

meshes = {}
for identity, file in job["assets"].items():
    bpy.ops.wm.stl_import(filepath=file)
    obj = bpy.context.object
    meshes[identity] = obj.data
    # Keep planar ends, sockets and hex flats sharp.
    if identity != "plate":
        obj.data.set_sharp_from_angle(angle=math.radians(27))
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    bpy.data.objects.remove(obj, do_unlink=True)

objects = []


def place(identity, finish, x=0, z=0, flip=False, turn=0):
    obj = bpy.data.objects.new(identity, meshes[identity])
    scene.collection.objects.link(obj)
    if not obj.data.materials:
        obj.data.materials.append(finish)
    obj.material_slots[0].link = "OBJECT"
    obj.material_slots[0].material = finish
    obj.location = (x, 0, z)
    obj.rotation_euler = (math.pi if flip else 0, 0, turn)
    objects.append(obj)


def render(path, eye=(0.52, -1.15, 0.82), wide=False, portrait=False):
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ Vector(v) for obj in objects for v in obj.bound_box]
    floor.location.z = min(p.z for p in points) - 0.045
    rotation = (-Vector(eye)).to_track_quat("-Z", "Y")
    projected = [rotation.inverted() @ p for p in points]
    lo = Vector([min(p[i] for p in projected) for i in range(3)])
    hi = Vector([max(p[i] for p in projected) for i in range(3)])
    ratio = 0.83 if portrait else (1.72 if wide else 1.36)
    camera.rotation_euler = rotation.to_euler()
    camera.location = rotation @ ((lo + hi) / 2) + Vector(eye).normalized() * 180
    # Blender fits the longer sensor axis. Account for that axis in portrait views.
    camera.data.ortho_scale = max(hi.x - lo.x, (hi.y - lo.y) * ratio) / min(1, ratio) * 1.10
    scene.render.resolution_x = 1080 if wide else 880
    scene.render.resolution_y = round(scene.render.resolution_x / ratio)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    objects.clear()


def adapter(part, x, z):
    d = part["details"]
    flipped = bool(d["sleeve_depth"])
    place(part["id"], black, x, z + (d["body_depth"] if flipped else 0), flipped)


backing_adapter = next(part for part in job["parts"] if all(
    part["details"][key] == value for key, value in (
        ("mounting", "to_flat"), ("size", "m3"), ("fastener_type", "nut"), ("oobb_type", "adapter")
    )
))


def joint(part, cap, x=0, stage=5, spread=False):
    d = part["details"]
    h = d["body_depth"]
    example = part["example"]
    nut = d["fastener_type"] == "nut"
    is_wood = d["fastener_type"] == "screw_wood"
    if stage >= 2:
        adapter(part, x, 16 if spread else (9 if stage == 2 else 0))
    if stage >= 3:
        if nut:
            place(example["hardware"], silver, x, h - d["seat_depth"] + (33 if spread else 0))
            place(example["counterpart"], silver, x, -24 if spread else 5, True)
        else:
            screw_length = 16 if is_wood else 10
            recess = 2.17 if is_wood else 0.84
            place(example["hardware"], gold if is_wood else silver, x, h - recess - screw_length + (39 if spread else 0))
    if not nut and not is_wood:
        show_backing = spread or stage == 1
        place(backing_adapter["id"], black, x, -16 if show_backing else -3, flip=True)
        place("hardware_nut_m3", silver, x, -30 if show_backing else -5, flip=True)
    if is_wood:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, -24 if spread else -11))
        block = bpy.context.object
        block.dimensions = (33, 24, 16)
        block.data.materials.append(wood)
        objects.append(block)
    if stage >= 4:
        proud = 0.2 if d["size"] == "m6" else 0
        lift = 53 if spread else (12 if stage == 4 else 0)
        place(cap["id"], yellow, x, cap["details"]["depth"] + lift + proud, True)


for part in job["parts"]:
    d = part["details"]
    folder = root / "parts" / part["id"]
    h = d["depth"]
    finish = black if d["oobb_type"] == "adapter" else yellow
    place(part["id"], finish, -8.5)
    place(part["id"], finish, 8.5, h, True)
    render(folder / "studio.png", eye=(0.35, -1, 0.85), wide=True)
    if d["oobb_type"] == "cap":
        continue
    cap = next(p for p in job["parts"] if p["details"]["oobb_type"] == "cap" and
               all(p["details"][k] == d[k] for k in ("size", "mounting", "fastener_type")))
    place("plate", plate_material, z=-3, turn=math.pi / 2)
    joint(part, cap, spread=True)
    render(folder / "installation.png", eye=(0.26, -1.4, 0.43), portrait=True)
    if d["size"] == "m6" and d["fastener_type"] == "nut":
        # Show the exploded joint beside the bolt head seated in the same pocket.
        place("plate", plate_material, z=-3)
        for x, exploded in ((-15, True), (15, False)):
            adapter(part, x, 12 if exploded else 0)
            floor_z = d["body_depth"] - d["seat_depth"]
            place(part["example"]["bolt_head_example"], silver, x, 28 if exploded else floor_z - 12)
            place("hardware_nut_m6", silver, x, -23 if exploded else -3, flip=True)
        place(cap["id"], yellow, -15, 60, flip=True)
        render(folder / "bolt_head.png", eye=(0.20, -1.3, 0.63), portrait=True)
    if d["fastener_type"] == "countersunk":
        kit = root / "output" / ("basic_set_" + d["mounting"])
        nut_part = next(p for p in job["parts"] if p["details"]["mounting"] == d["mounting"]
                        and p["details"]["size"] == "m6" and p["details"]["oobb_type"] == "adapter")
        nut_cap = next(p for p in job["parts"] if p["details"]["mounting"] == d["mounting"]
                       and p["details"]["size"] == "m6" and p["details"]["oobb_type"] == "cap")
        place("plate", plate_material, z=-3)
        joint(part, cap, -15, spread=True)
        joint(nut_part, nut_cap, 15, spread=True)
        render(kit / "exploded.png", eye=(0.22, -1.4, 0.47), portrait=True)
        place("plate", plate_material, z=-3)
        joint(part, cap, -15, 5)
        joint(part, cap, 0, 3)
        joint(nut_part, nut_cap, 15, 4)
        render(kit / "assembled.png", eye=(0.44, -1.2, 0.92), wide=True)
        place("plate", plate_material, z=-3, turn=math.pi / 2)
        joint(part, cap, stage=5)
        render(kit / "assembly" / "finished.png")
        for step in range(1, 5):
            place("plate", plate_material, z=-3, turn=math.pi / 2)
            joint(part, cap, stage=step)
            render(kit / "assembly" / f"step_{step}.png", eye=(0.36, -1.3, 0.38) if step < 3 else (0.52, -1.15, 0.82))

for identity in meshes:
    if identity.startswith("hardware_") or identity == "plate":
        finish = plate_material if identity == "plate" else (gold if "_wood_" in identity else silver)
        place(identity, finish, turn=math.pi / 2 if identity == "plate" else 0)
        render(root / "source_file" / "previews" / (identity + ".png"))
