"""Blender script: dense textured GLB -> QuadriFlow quad mesh with UVs and PBR maps baked from the original.

Run through quad.sh, or:
  blender -b --factory-startup --python quad.py -- <in.glb> <out.glb> <target_faces> [texture_size] [GPU|CPU]
Also saves <out>.blend with packed textures. Prints a STATS line (faces, quad ratio, time).
"""
import math, sys, time
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst, faces = argv[0], argv[1], int(argv[2])
size = int(argv[3]) if len(argv) > 3 else 2048
device = argv[4] if len(argv) > 4 else "GPU"
t0 = time.time()


def step(msg):
    print(f"STEP {time.time() - t0:5.0f}s {msg}", flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
hi = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
hi.name = "source"

lo = hi.copy()
lo.data = hi.data.copy()
lo.name = "quad"
bpy.context.scene.collection.objects.link(lo)
bpy.ops.object.select_all(action="DESELECT")
lo.select_set(True)
bpy.context.view_layer.objects.active = lo
step(f"imported {len(hi.data.polygons)} faces")
# Always go through a voxel remesh: it welds the glTF UV-seam splits, closes holes and drops inner shells,
# so QuadriFlow gets one clean manifold surface. 1/160 of the size is far finer than the final quads.
lo.data.remesh_voxel_size = max(lo.dimensions) / 160
bpy.ops.object.voxel_remesh()
step(f"voxel remesh: {len(lo.data.polygons)} faces")
# QuadriFlow's pre-check rejects edges shorter than an absolute 1e-4, and voxel remesh of a unit-size
# mesh leaves a few. Run it on a 100x copy, then scale back.
lo.scale = (100, 100, 100)
bpy.ops.object.transform_apply(scale=True)
step(f"QuadriFlow on {len(lo.data.polygons)} faces")
n_before = len(lo.data.polygons)
# use_preserve_sharp makes QuadriFlow loop forever on the fox and the lantern (10 s without it).
bpy.ops.object.quadriflow_remesh(mode="FACES", target_faces=faces, use_preserve_sharp=False, use_mesh_symmetry=False, seed=0)
if len(lo.data.polygons) == n_before:
    sys.exit("QuadriFlow failed (mesh unchanged), see log")
lo.scale = (0.01, 0.01, 0.01)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.shade_smooth()
t_remesh = time.time() - t0

step(f"QuadriFlow done: {len(lo.data.polygons)} faces")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
bpy.ops.object.mode_set(mode="OBJECT")

# Target material with one image node per baked map.
lo.data.materials.clear()
mat = bpy.data.materials.new("quad_pbr")
mat.use_nodes = True
lo.data.materials.append(mat)
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
maps = {}
for name, colorspace in (("base_color", "sRGB"), ("roughness", "Non-Color"), ("metallic", "Non-Color"), ("normal", "Non-Color")):
    img = bpy.data.images.new(f"quad_{name}", size, size, alpha=False, float_buffer=False)
    img.colorspace_settings.name = colorspace
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = img
    maps[name] = node

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
try:
    assert device == "GPU", "CPU requested"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:
    print("GPU bake unavailable, using CPU:", e)

# Bake raw material values through emission: Cycles' DIFFUSE color pass is scaled by (1 - metallic) and
# (1 - transmission), which turned metal dark and the lantern glass black, and metallic has no bake pass.
sources = []
for m in hi.data.materials:
    p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m and m.use_nodes else None
    if p is not None:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        emit = m.node_tree.nodes.new("ShaderNodeEmission")
        m.node_tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
        sources.append((m.node_tree, p, emit))


def route(socket_name):
    for tree, p, emit in sources:
        src = p.inputs[socket_name]
        for l in list(emit.inputs["Color"].links):
            tree.links.remove(l)
        if src.is_linked:
            tree.links.new(src.links[0].from_socket, emit.inputs["Color"])
        else:
            v = src.default_value
            emit.inputs["Color"].default_value = tuple(v)[:3] + (1,) if hasattr(v, "__len__") else (v, v, v, 1)


bpy.ops.object.select_all(action="DESELECT")
hi.select_set(True)
lo.select_set(True)
bpy.context.view_layer.objects.active = lo
extrusion = 0.01 * max(lo.dimensions)
bake = scene.render.bake
bake.use_selected_to_active = True
bake.cage_extrusion = extrusion
bake.max_ray_distance = 4 * extrusion
bake.margin = 8
for name, socket in (("base_color", "Base Color"), ("roughness", "Roughness"), ("metallic", "Metallic"), ("normal", None)):
    nt.nodes.active = maps[name]
    step(f"bake {name}")
    if socket:
        route(socket)
        bpy.ops.object.bake(type="EMIT")
    else:
        # Normal needs the real shading (incl. the source normal map): restore the BSDF output.
        for tree, p, emit in sources:
            out = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
            tree.links.new(p.outputs["BSDF"], out.inputs["Surface"])
        bpy.ops.object.bake(type="NORMAL")
    maps[name].image.pack()

links = nt.links
links.new(maps["base_color"].outputs["Color"], bsdf.inputs["Base Color"])
links.new(maps["roughness"].outputs["Color"], bsdf.inputs["Roughness"])
links.new(maps["metallic"].outputs["Color"], bsdf.inputs["Metallic"])
nmap = nt.nodes.new("ShaderNodeNormalMap")
links.new(maps["normal"].outputs["Color"], nmap.inputs["Color"])
links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

bpy.data.objects.remove(hi)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB")
bpy.ops.wm.save_as_mainfile(filepath=dst[:-4] + ".blend")

polys = lo.data.polygons
quads = sum(1 for p in polys if len(p.vertices) == 4)
print(f"STATS faces={len(polys)} quads={quads / len(polys):.1%} verts={len(lo.data.vertices)} "
      f"remesh={t_remesh:.0f}s total={time.time() - t0:.0f}s")
