"""Blender script: GLB -> 4 textured views + 4 wireframe views (Workbench), saved as <prefix>_tex<i>.png / <prefix>_wire<i>.png.

Run through sheet.sh, or:
  blender -b --factory-startup --python render.py -- <in.glb> <out_prefix> [size=512]
"""
import math, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, prefix = argv[0], argv[1]
size = int(argv[2]) if len(argv) > 2 else 512

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
lo = Vector(min(p[i] for p in pts) for i in range(3))
hi = Vector(max(p[i] for p in pts) for i in range(3))
center, radius = (lo + hi) / 2, (hi - lo).length / 2

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = size
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
shading = scene.display.shading
shading.light = "STUDIO"

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 50
scene.collection.objects.link(cam)
scene.camera = cam
dist = radius / math.tan(cam.data.angle / 2) * 1.05

# Wireframe overlays: one wire copy per mesh, shown only in the wire pass.
wires = []
for o in objs:
    w = o.copy()
    w.data = o.data
    scene.collection.objects.link(w)
    mod = w.modifiers.new("wire", "WIREFRAME")
    mod.thickness = radius * 0.0025
    mod.use_relative_offset = False
    mod.use_even_offset = False
    w.color = (0.05, 0.05, 0.05, 1)
    wires.append(w)

# glTF is Y-up, Blender imports Z-up: orbit around Z.
for i, az in enumerate((30, 120, 210, 300)):
    a, el = math.radians(az), math.radians(20)
    cam.location = center + Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))) * dist
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    for name, color_type in (("tex", "TEXTURE"), ("wire", "OBJECT")):
        shading.color_type = color_type
        for w in wires:
            w.hide_render = name == "tex"
        for o in objs:
            o.color = (0.8, 0.8, 0.8, 1)
        scene.render.filepath = f"{prefix}_{name}{i}.png"
        bpy.ops.render.render(write_still=True)
