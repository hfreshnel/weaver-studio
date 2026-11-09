"""Procedural storm-night lighthouse set for the 10 s short (Blender 5.2, run headless).

  blender -b --python scene.py -- <out.blend> [boat.glb]

Builds: heightfield headland + rock/grass shader, lighthouse (tower, red band, gallery, lantern, dome),
keeper's cottage, Ocean modifier sea with foam, stormy procedural sky, volumetric fog, rotating twin beam,
the TRELLIS.2 boat bobbing on the sampled ocean surface, cameras CamS1 (frames 1-60) and CamS4 (frames 101-172).
Units: metres, Z up, sea level z = 0.
"""
import math, sys
import bpy, bmesh
from mathutils import Vector, noise, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/lh.blend"
BOAT = argv[1] if len(argv) > 1 else None
FPS = 24
SKY, FOG, MOON = 0.9, 0.0016, 0.9
LAMP_ON = 100            # lamp switched off before this frame, on after (S1 = 1..60, S4 = 101..172)
L = Vector((2.0, 50.0, 0.0))  # lighthouse foot (x, y); z found on the terrain

bpy.ops.wm.read_factory_settings(use_empty=True)
# Blender 5 layered actions: set linear as the default instead of patching fcurves afterwards
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, 176


def mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def obj(name, mesh):
    o = bpy.data.objects.new(name, mesh)
    sc.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- terrain (headland)
def shore(x):
    """Promontory: the coast recedes on both sides of a rocky point at y ~ 32."""
    return 32.0 + 0.011 * x * x + 6.0 * noise.noise(Vector((x / 30.0, 0.3, 0.7))) + 3.0 * noise.noise(Vector((x / 8.0, 1.7, 0.2)))


def height(x, y):
    d = y - shore(x)
    cliff = 24.0 / (1.0 + math.exp(-d / 2.4))          # steep sigmoid cliff ~24 m high
    plateau = 2.5 * noise.fractal(Vector((x / 40.0, y / 40.0, 0.1)), 0.6, 2.0, 4) if d > 4 else 0.0
    rough = 2.2 * noise.fractal(Vector((x / 7.0, y / 7.0, 3.3)), 0.7, 2.0, 5)  # rock breakup everywhere
    rocks = 0.0
    if -14 < d < 2:                                    # boulders at the foot of the cliff
        rocks = max(0.0, 3.5 * noise.noise(Vector((x / 4.0, y / 4.0, 5.0))) + 1.0) * (1 - abs(d + 6) / 8)
    base = -3.0 if d < -18 else -3.0 + 0.2 * (d + 18)   # seabed slopes up to the cliff
    return max(base, min(cliff + plateau, 31.0)) + rough * (0.4 if d > 4 else 1.0) + max(0.0, rocks)


def terrain():
    nx, ny, x0, x1, y0, y1 = 480, 340, -110.0, 110.0, 5.0, 170.0
    bm = bmesh.new()
    vs = []
    for j in range(ny):
        y = y0 + (y1 - y0) * j / (ny - 1)
        row = []
        for i in range(nx):
            x = x0 + (x1 - x0) * i / (nx - 1)
            row.append(bm.verts.new((x, y, height(x, y))))
        vs.append(row)
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new("terrain")
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    o = obj("Terrain", me)
    tex = bpy.data.textures.new("RockDisp", "CLOUDS"); tex.noise_scale = 3.5; tex.noise_depth = 4; tex.noise_basis = "VORONOI_F2"
    sub = o.modifiers.new("Sub", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = sub.render_levels = 1
    dm = o.modifiers.new("Rock", "DISPLACE"); dm.texture = tex; dm.texture_coords = "GLOBAL"; dm.strength = 2.6; dm.mid_level = 0.5
    m, n, ln, b = mat("Rock")
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ"); ln.new(geo.outputs["Normal"], sep.inputs[0])
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 10
    ln.new(tc.outputs["Object"], nz.inputs["Vector"])
    rock = n.new("ShaderNodeValToRGB"); rock.color_ramp.elements[0].color = (0.035, 0.033, 0.032, 1); rock.color_ramp.elements[1].color = (0.13, 0.12, 0.11, 1)
    ln.new(nz.outputs["Fac"], rock.inputs[0])
    grass_mask = n.new("ShaderNodeMapRange"); grass_mask.inputs["From Min"].default_value = 0.78; grass_mask.inputs["From Max"].default_value = 0.9
    ln.new(sep.outputs["Z"], grass_mask.inputs["Value"])
    hz = n.new("ShaderNodeSeparateXYZ"); ln.new(geo.outputs["Position"], hz.inputs[0])
    hmask = n.new("ShaderNodeMapRange"); hmask.inputs["From Min"].default_value = 18; hmask.inputs["From Max"].default_value = 22
    ln.new(hz.outputs["Z"], hmask.inputs["Value"])
    gm = n.new("ShaderNodeMath"); gm.operation = "MULTIPLY"; ln.new(grass_mask.outputs[0], gm.inputs[0]); ln.new(hmask.outputs[0], gm.inputs[1])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[7].default_value = (0.05, 0.08, 0.035, 1)
    ln.new(gm.outputs[0], mix.inputs[0]); ln.new(rock.outputs[0], mix.inputs[6])
    ln.new(mix.outputs[2], b.inputs["Base Color"])
    wet = n.new("ShaderNodeMapRange"); wet.inputs["From Min"].default_value = 0; wet.inputs["From Max"].default_value = 6
    wet.inputs["To Min"].default_value = 0.15; wet.inputs["To Max"].default_value = 0.6
    ln.new(hz.outputs["Z"], wet.inputs["Value"]); ln.new(wet.outputs[0], b.inputs["Roughness"])
    bmp = n.new("ShaderNodeBump"); bmp.inputs["Strength"].default_value = 0.9; bmp.inputs["Distance"].default_value = 0.6
    nz2 = n.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 3.0; nz2.inputs["Detail"].default_value = 8
    ln.new(tc.outputs["Object"], nz2.inputs["Vector"])
    squash = n.new("ShaderNodeMapping"); squash.inputs["Scale"].default_value = (0.25, 0.25, 3.0)   # horizontal strata
    ln.new(tc.outputs["Object"], squash.inputs["Vector"])
    strata = n.new("ShaderNodeTexNoise"); strata.inputs["Scale"].default_value = 0.6; strata.inputs["Detail"].default_value = 6
    ln.new(squash.outputs[0], strata.inputs["Vector"])
    vor = n.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 0.8; vor.feature = "F1"
    ln.new(tc.outputs["Object"], vor.inputs["Vector"])
    h1 = n.new("ShaderNodeMath"); h1.operation = "MULTIPLY_ADD"; h1.inputs[1].default_value = 0.6
    ln.new(strata.outputs["Fac"], h1.inputs[0]); ln.new(vor.outputs["Distance"], h1.inputs[2])
    h2 = n.new("ShaderNodeMath"); h2.operation = "MULTIPLY_ADD"; h2.inputs[1].default_value = 0.25
    ln.new(nz2.outputs["Fac"], h2.inputs[0]); ln.new(h1.outputs[0], h2.inputs[2])
    ln.new(h2.outputs[0], bmp.inputs["Height"]); ln.new(bmp.outputs[0], b.inputs["Normal"])
    o.data.materials.append(m)
    return o


# ---------------------------------------------------------------- lighthouse
def cyl(name, r1, r2, h, z, verts=48, m=None, loc=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=h, location=(loc or L).to_tuple()[:2] + (z + h / 2,))
    o = bpy.context.active_object; o.name = name
    bpy.ops.object.shade_smooth()
    if m: o.data.materials.append(m)
    return o


def lighthouse(gz):
    tw, n, ln, b = mat("TowerPaint")
    sxyz = n.new("ShaderNodeSeparateXYZ"); tc = n.new("ShaderNodeTexCoord"); ln.new(tc.outputs["Object"], sxyz.inputs[0])
    band = n.new("ShaderNodeMapRange"); band.interpolation_type = "STEPPED"; band.inputs["Steps"].default_value = 1
    # object-space z of the tower runs -10..10: red band between z 0 and 4.5
    band.inputs["From Min"].default_value = -0.5; band.inputs["From Max"].default_value = 1.5
    ln.new(sxyz.outputs["Z"], band.inputs["Value"])
    lo = n.new("ShaderNodeMath"); lo.operation = "LESS_THAN"; lo.inputs[1].default_value = 4.5; ln.new(sxyz.outputs["Z"], lo.inputs[0])
    hi = n.new("ShaderNodeMath"); hi.operation = "GREATER_THAN"; hi.inputs[1].default_value = 0.0; ln.new(sxyz.outputs["Z"], hi.inputs[0])
    both = n.new("ShaderNodeMath"); both.operation = "MULTIPLY"; ln.new(lo.outputs[0], both.inputs[0]); ln.new(hi.outputs[0], both.inputs[1])
    dirt = n.new("ShaderNodeTexNoise"); dirt.inputs["Scale"].default_value = 1.2; dirt.inputs["Detail"].default_value = 6
    ln.new(tc.outputs["Object"], dirt.inputs["Vector"])
    white = n.new("ShaderNodeMix"); white.data_type = "RGBA"; white.inputs[6].default_value = (0.55, 0.55, 0.52, 1); white.inputs[7].default_value = (0.75, 0.74, 0.70, 1)
    ln.new(dirt.outputs["Fac"], white.inputs[0])
    col = n.new("ShaderNodeMix"); col.data_type = "RGBA"; col.inputs[7].default_value = (0.42, 0.03, 0.025, 1)
    ln.new(both.outputs[0], col.inputs[0]); ln.new(white.outputs[2], col.inputs[6]); ln.new(col.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    tower = cyl("Tower", 3.1, 2.25, 20, gz - 1, m=tw)
    metal, *_r, mb = mat("DarkMetal"); mb.inputs["Base Color"].default_value = (0.02, 0.025, 0.025, 1); mb.inputs["Metallic"].default_value = 0.9; mb.inputs["Roughness"].default_value = 0.35
    red, *_r, rb = mat("DomeRed"); rb.inputs["Base Color"].default_value = (0.3, 0.02, 0.02, 1); rb.inputs["Metallic"].default_value = 0.6; rb.inputs["Roughness"].default_value = 0.3
    top = gz + 19
    cyl("Gallery", 3.35, 3.35, 0.35, top, m=metal)
    cyl("LanternBase", 2.0, 2.0, 1.0, top + 0.35, m=tw)
    # railing: posts + rings
    for k in range(24):
        a = 2 * math.pi * k / 24
        p = L + Vector((3.2 * math.cos(a), 3.2 * math.sin(a), 0))
        cyl(f"Post{k}", 0.04, 0.04, 1.1, top + 0.35, verts=6, m=metal, loc=p)
    for zz in (top + 0.85, top + 1.45):
        bpy.ops.mesh.primitive_torus_add(major_radius=3.2, minor_radius=0.035, location=(L.x, L.y, zz), major_segments=64, minor_segments=6)
        bpy.context.active_object.data.materials.append(metal)
    # lantern: glass + mullions + lamp
    glass, gn, gl, gb = mat("Glass")
    gb.inputs["Base Color"].default_value = (0.6, 0.7, 0.75, 1); gb.inputs["Roughness"].default_value = 0.05
    gb.inputs["Alpha"].default_value = 0.12  # alpha, not transmission: Cycles blocks direct light behind refractive glass
    glass.surface_render_method = "BLENDED" if hasattr(glass, "surface_render_method") else glass.blend_method
    cyl("LanternGlass", 1.75, 1.75, 2.8, top + 1.35, verts=12, m=glass)
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        p = L + Vector((1.76 * math.cos(a), 1.76 * math.sin(a), 0))
        cyl(f"Mullion{k}", 0.05, 0.05, 2.8, top + 1.35, verts=6, m=metal, loc=p)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.85, location=(L.x, L.y, top + 4.15), segments=48, ring_count=24)
    dome = bpy.context.active_object; dome.name = "Dome"; dome.scale.z = 0.6; bpy.ops.object.shade_smooth(); dome.data.materials.append(red)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(L.x, L.y, top + 5.4)); bpy.context.active_object.data.materials.append(metal)
    # the lamp itself (emission animated on at LAMP_ON)
    lm, ln_, ll, lb = mat("Lamp")
    lb.inputs["Base Color"].default_value = (1, 0.85, 0.6, 1); lb.inputs["Emission Color"].default_value = (1.0, 0.86, 0.62, 1)
    lb.inputs["Emission Strength"].default_value = 0.0; lb.inputs["Emission Strength"].keyframe_insert("default_value", frame=LAMP_ON)
    lb.inputs["Emission Strength"].default_value = 60.0; lb.inputs["Emission Strength"].keyframe_insert("default_value", frame=LAMP_ON + 1)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(L.x, L.y, top + 2.6)); bpy.context.active_object.name = "LampBulb"
    bpy.context.active_object.visible_shadow = False  # the beam spots sit inside the bulb
    bpy.context.active_object.data.materials.append(lm)
    # windows on the tower (dark recesses)
    win, *_r, wb = mat("Window"); wb.inputs["Base Color"].default_value = (0.01, 0.012, 0.015, 1); wb.inputs["Roughness"].default_value = 0.1
    warm, *_r, wwb = mat("WarmWindow"); wwb.inputs["Emission Color"].default_value = (1, 0.55, 0.22, 1); wwb.inputs["Emission Strength"].default_value = 8
    for i, (zz, a) in enumerate([(4, -1.2), (10, -1.0), (15.5, -1.35)]):
        r = 3.1 - (3.1 - 2.25) * (zz + 1) / 20
        bpy.ops.mesh.primitive_cube_add(size=1, location=(L.x + r * math.cos(a), L.y + r * math.sin(a), gz + zz))
        w = bpy.context.active_object; w.scale = (0.25, 0.55, 0.9); w.rotation_euler.z = a
        w.data.materials.append(warm if i == 0 else win)
    return top


def cottage(gz):
    paint, *_r, pb = mat("Cottage"); pb.inputs["Base Color"].default_value = (0.6, 0.6, 0.57, 1); pb.inputs["Roughness"].default_value = 0.7
    roof, *_r, rb = mat("Roof"); rb.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1); rb.inputs["Roughness"].default_value = 0.35
    warm, *_r, wb = mat("CottageWindow"); wb.inputs["Emission Color"].default_value = (1, 0.55, 0.22, 1); wb.inputs["Emission Strength"].default_value = 12
    c = L + Vector((-9.5, 3.0, 0))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(c.x, c.y, gz + 1.6)); h = bpy.context.active_object; h.scale = (9, 5, 3.6); h.data.materials.append(paint)
    bm = bmesh.new()
    pts = [(-4.8, -2.8, 3.4), (4.8, -2.8, 3.4), (4.8, 2.8, 3.4), (-4.8, 2.8, 3.4), (-4.8, 0, 5.4), (4.8, 0, 5.4)]
    v = [bm.verts.new(Vector(p) + Vector((c.x, c.y, gz))) for p in pts]
    for f in ((v[0], v[1], v[5], v[4]), (v[3], v[4], v[5], v[2]), (v[0], v[4], v[3]), (v[1], v[2], v[5])):
        bm.faces.new(f)
    me = bpy.data.meshes.new("roof"); bm.to_mesh(me); ro = obj("Roof", me); ro.data.materials.append(roof)
    for dx in (-2.5, 1.0, 3.0):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(c.x + dx, c.y - 2.52, gz + 1.9)); w = bpy.context.active_object; w.scale = (0.9, 0.08, 1.1)
        w.data.materials.append(warm)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(c.x + 3.2, c.y + 1, gz + 5.3)); bpy.context.active_object.scale = (0.7, 0.7, 1.6)
    bpy.context.active_object.data.materials.append(paint)


# ---------------------------------------------------------------- ocean
def ocean():
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = "Ocean"
    md = o.modifiers.new("Ocean", "OCEAN")
    md.geometry_mode = "GENERATE"
    md.resolution = 16; md.viewport_resolution = 4
    md.spatial_size = 150; md.repeat_x = md.repeat_y = 3
    md.wave_scale = 4.0; md.wave_scale_min = 0.02; md.choppiness = 1.5; md.wind_velocity = 26
    md.wave_alignment = 0.35; md.wave_direction = math.radians(80); md.random_seed = 7
    md.use_foam = True; md.foam_layer_name = "foam"; md.foam_coverage = 0.25; md.use_normals = True
    md.time = 0.0; md.keyframe_insert("time", frame=0)
    md.time = 180 / FPS; md.keyframe_insert("time", frame=180)
    for fc in (o.animation_data.action.fcurves if hasattr(o.animation_data.action, "fcurves") else []):
        for k in fc.keyframe_points: k.interpolation = "LINEAR"
    o.location = (-225 + 90 * 2.5 - 45, -150, 0)  # tiles span 450 m; centre them in front of the headland
    o.location = (-225, -190, 0)
    m, n, ln, b = mat("Sea")
    b.inputs["Base Color"].default_value = (0.004, 0.012, 0.018, 1); b.inputs["Roughness"].default_value = 0.12
    b.inputs["Specular IOR Level"].default_value = 0.3
    att = n.new("ShaderNodeAttribute"); att.attribute_name = "foam"
    ramp = n.new("ShaderNodeMapRange"); ramp.inputs["From Min"].default_value = 0.25; ramp.inputs["From Max"].default_value = 0.9
    ln.new(att.outputs["Fac"], ramp.inputs["Value"])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[6].default_value = (0.004, 0.012, 0.018, 1); mix.inputs[7].default_value = (0.5, 0.55, 0.58, 1)
    ln.new(ramp.outputs[0], mix.inputs[0]); ln.new(mix.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.05; rr.inputs["To Max"].default_value = 0.8
    ln.new(ramp.outputs[0], rr.inputs["Value"]); ln.new(rr.outputs[0], b.inputs["Roughness"])
    # chop: small wind ripples break the flat sky reflection in the foreground (read as snow otherwise)
    tcw = n.new("ShaderNodeTexCoord"); chop = n.new("ShaderNodeTexNoise"); chop.noise_dimensions = "4D"
    chop.inputs["Scale"].default_value = 0.9; chop.inputs["Detail"].default_value = 9; chop.inputs["Roughness"].default_value = 0.65
    chop.inputs["W"].default_value = 0; chop.inputs["W"].keyframe_insert("default_value", frame=0)
    chop.inputs["W"].default_value = 6; chop.inputs["W"].keyframe_insert("default_value", frame=180)
    ln.new(tcw.outputs["Object"], chop.inputs["Vector"])
    cb = n.new("ShaderNodeBump"); cb.inputs["Strength"].default_value = 0.45; cb.inputs["Distance"].default_value = 0.5
    ln.new(chop.outputs["Fac"], cb.inputs["Height"]); ln.new(cb.outputs[0], b.inputs["Normal"])
    o.data.materials.append(m)
    return o


# ---------------------------------------------------------------- sky + fog
def world():
    w = bpy.data.worlds.new("Storm"); sc.world = w; w.use_nodes = True
    n, ln = w.node_tree.nodes, w.node_tree.links
    bg = n["Background"]
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); ln.new(tc.outputs["Generated"], sep.inputs[0])
    grad = n.new("ShaderNodeMapRange"); grad.inputs["From Min"].default_value = 0.0; grad.inputs["From Max"].default_value = 0.6
    vz = n.new("ShaderNodeSeparateXYZ"); ln.new(tc.outputs["Window"], vz.inputs[0])
    # view-direction height (Generated coords of the world = direction)
    ln.new(sep.outputs["Z"], grad.inputs["Value"])
    cl = n.new("ShaderNodeTexNoise"); cl.noise_dimensions = "4D"; cl.inputs["Scale"].default_value = 4.5; cl.inputs["Detail"].default_value = 12; cl.inputs["Roughness"].default_value = 0.62
    ln.new(tc.outputs["Generated"], cl.inputs["Vector"])
    cl.inputs["W"].default_value = 0.0; cl.inputs["W"].keyframe_insert("default_value", frame=0)
    cl.inputs["W"].default_value = 0.35; cl.inputs["W"].keyframe_insert("default_value", frame=180)
    cramp = n.new("ShaderNodeValToRGB")
    cramp.color_ramp.elements[0].position = 0.38; cramp.color_ramp.elements[0].color = (0.006, 0.008, 0.013, 1)
    cramp.color_ramp.elements[1].position = 0.68; cramp.color_ramp.elements[1].color = (0.16, 0.19, 0.25, 1)
    ln.new(cl.outputs["Fac"], cramp.inputs[0])
    hor = n.new("ShaderNodeMix"); hor.data_type = "RGBA"; hor.inputs[6].default_value = (0.04, 0.06, 0.085, 1)
    ln.new(grad.outputs[0], hor.inputs[0]); ln.new(cramp.outputs[0], hor.inputs[7])
    ln.new(hor.outputs[2], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.0
    bg.inputs["Strength"].default_value = SKY


def fog():
    """Bounded homogeneous fog (a world volume would swallow the sky in Cycles)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 25, 45))
    o = bpy.context.active_object; o.name = "Fog"; o.scale = (420, 420, 100)
    m = bpy.data.materials.new("Fog"); m.use_nodes = True
    n, ln = m.node_tree.nodes, m.node_tree.links
    n.remove(n["Principled BSDF"])
    vol = n.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = FOG
    vol.inputs["Color"].default_value = (0.75, 0.82, 0.9, 1); vol.inputs["Anisotropy"].default_value = 0.45
    ln.new(vol.outputs[0], n["Material Output"].inputs["Volume"])
    o.data.materials.append(m)
    o.visible_shadow = False


def beam(top):
    z = top + 2.6
    rig = bpy.data.objects.new("BeamRig", None); sc.collection.objects.link(rig); rig.location = (L.x, L.y, z)
    for k, yaw in enumerate((0, math.pi)):
        ld = bpy.data.lights.new(f"Beam{k}", "SPOT"); ld.energy = 0.0; ld.spot_size = math.radians(7); ld.spot_blend = 0.6
        ld.color = (1.0, 0.9, 0.72); ld.shadow_soft_size = 0.4
        if hasattr(ld, "volume_factor"): ld.volume_factor = 1.0
        ld.keyframe_insert("energy", frame=LAMP_ON); ld.energy = 4.0e6; ld.keyframe_insert("energy", frame=LAMP_ON + 1)
        lo = bpy.data.objects.new(f"Beam{k}", ld); sc.collection.objects.link(lo); lo.parent = rig
        lo.rotation_euler = Euler((math.radians(88.5), 0, yaw - math.pi / 2), "XYZ")
    # warm fill inside the lantern
    pl = bpy.data.lights.new("LanternFill", "POINT"); pl.energy = 0; pl.color = (1, 0.8, 0.55); pl.shadow_soft_size = 0.5
    pl.keyframe_insert("energy", frame=LAMP_ON); pl.energy = 3000; pl.keyframe_insert("energy", frame=LAMP_ON + 1)
    po = bpy.data.objects.new("LanternFill", pl); sc.collection.objects.link(po); po.location = (L.x, L.y, z)
    return rig


def lightning(frames):
    """Sheet lightning behind the clouds: a cold sun light flickering over a few frames (S1 opening beat)."""
    ld = bpy.data.lights.new("Lightning", "SUN"); ld.color = (0.75, 0.82, 1.0); ld.angle = math.radians(20)
    o = bpy.data.objects.new("Lightning", ld); sc.collection.objects.link(o); o.rotation_euler = Euler((math.radians(70), 0, math.radians(160)))
    ld.energy = 0; ld.keyframe_insert("energy", frame=1)
    for f, e in frames:
        ld.energy = e; ld.keyframe_insert("energy", frame=f)
    o.visible_volume_scatter = False          # flash the surfaces and the sky, not the fog (milky otherwise)
    bg = sc.world.node_tree.nodes["Background"].inputs["Strength"]
    bg.keyframe_insert("default_value", frame=1)
    for f, e in frames:
        bg.default_value = SKY * (1 + 0.6 * e); bg.keyframe_insert("default_value", frame=f)


def moon():
    ld = bpy.data.lights.new("MoonKey", "SUN"); ld.energy = MOON; ld.color = (0.55, 0.65, 0.85); ld.angle = math.radians(3)
    o = bpy.data.objects.new("MoonKey", ld); sc.collection.objects.link(o); o.rotation_euler = Euler((math.radians(60), 0, math.radians(-140)))


# ---------------------------------------------------------------- boat
def ocean_patch(oc, center, radius, frame):
    sc.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = oc.evaluated_get(dg)
    me = ev.to_mesh()
    mw = oc.matrix_world
    pts = [mw @ v.co for v in me.vertices if (Vector(((mw @ v.co).x, (mw @ v.co).y)) - center).length < radius]
    ev.to_mesh_clear()
    return pts


def boat(path, oc, pos, yaw):
    bpy.ops.import_scene.gltf(filepath=path)
    parts = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    root = bpy.data.objects.new("Boat", None); sc.collection.objects.link(root)
    for p in parts: p.parent = root
    # normalise: longest horizontal side -> 11 m, keel at z=0
    bpy.context.view_layer.update()
    co = [p.matrix_world @ Vector(c) for p in parts for c in p.bound_box]
    mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co))); mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    s = 11.0 / max(mx.x - mn.x, mx.y - mn.y)
    for p in parts:
        p.location = (p.location - Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z + 0.17 * (mx.z - mn.z)))) * s
        p.scale = p.scale * s
    root.location = (pos.x, pos.y, 0); root.rotation_euler.z = yaw
    for p in parts:   # not in S1 (frames < 100): it would sit on the frame edge
        p.hide_render = True; p.keyframe_insert("hide_render", frame=1)
        p.hide_render = False; p.keyframe_insert("hide_render", frame=99)
    # follow the waves: plane fit of the evaluated ocean around the hull, every 2 frames
    for f in range(LAMP_ON - 2, 175, 2):
        pts = ocean_patch(oc, pos, 5.5, f)
        if len(pts) < 6: continue
        cz = sum(p.z for p in pts) / len(pts)
        cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
        sxx = sum((p.x - cx) ** 2 for p in pts); syy = sum((p.y - cy) ** 2 for p in pts); sxy = sum((p.x - cx) * (p.y - cy) for p in pts)
        sxz = sum((p.x - cx) * (p.z - cz) for p in pts); syz = sum((p.y - cy) * (p.z - cz) for p in pts)
        det = sxx * syy - sxy * sxy
        ax = (sxz * syy - syz * sxy) / det if det else 0; ay = (syz * sxx - sxz * sxy) / det if det else 0
        root.location.z = cz
        # slope -> tilt in world axes, damped (a hull does not follow every ripple)
        root.rotation_euler = Euler((math.atan(ay) * 0.7, -math.atan(ax) * 0.7, yaw), "XYZ")
        root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", frame=f)
    # running lights
    for nm, off, colr in (("Port", (-1.5, 1.0, 3.2), (1, 0.1, 0.05)), ("Mast", (0, 0.5, 6.5), (1, 0.9, 0.7))):
        ld = bpy.data.lights.new(nm, "POINT"); ld.energy = 60; ld.color = colr; ld.shadow_soft_size = 0.1
        lo = bpy.data.objects.new(nm, ld); sc.collection.objects.link(lo); lo.parent = root; lo.location = off
        lo.hide_render = True; lo.keyframe_insert("hide_render", frame=1); lo.hide_render = False; lo.keyframe_insert("hide_render", frame=99)
    return root


# ---------------------------------------------------------------- cameras
def camera(name, frames_pos, target_pos, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36
    cd.dof.use_dof = False
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    tgt = bpy.data.objects.new(name + "_tgt", None); sc.collection.objects.link(tgt)
    tc = co.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
    for f, p in frames_pos:
        co.location = p; co.keyframe_insert("location", frame=f)
    for f, p in target_pos:
        tgt.location = p; tgt.keyframe_insert("location", frame=f)
    return co


def render_settings():
    r = sc.render
    r.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE_NEXT"
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.use_motion_blur = True; r.motion_blur_shutter = 0.5
    e = sc.eevee
    e.taa_render_samples = 48
    for k, v in dict(volumetric_tile_size="4", volumetric_samples=96, volumetric_start=1.0, volumetric_end=500.0,
                     use_volumetric_shadows=True, volumetric_shadow_samples=24, use_raytracing=True).items():
        if hasattr(e, k): setattr(e, k, v)
    sc.view_settings.view_transform = "AgX"; sc.view_settings.exposure = 0.5
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError: pass
    r.image_settings.file_format = "PNG"


# ---------------------------------------------------------------- build
terr = terrain()
gz = height(L.x, L.y)
top = lighthouse(gz)
cottage(height(L.x - 9.5, L.y + 3))
oc = ocean()
world(); moon(); fog()
lightning([(4, 0), (5, 3.2), (6, 0.8), (7, 2.4), (8, 0.5), (10, 0)])
rig = beam(top)
# beam: 36 deg/s counter-clockwise; beam 0 points at the boat at frame 140
BOATP = Vector((22.0, -8.0))
boat_ang = math.degrees(math.atan2(BOATP.y - L.y, BOATP.x - L.x))
rig.rotation_euler.z = math.radians(boat_ang - 40 * 1.5); rig.keyframe_insert("rotation_euler", frame=LAMP_ON)
rig.rotation_euler.z = math.radians(boat_ang - 40 * 1.5 + 270); rig.keyframe_insert("rotation_euler", frame=LAMP_ON + 180)
for fc in rig.animation_data.action.fcurves if hasattr(rig.animation_data.action, "fcurves") else []:
    for k in fc.keyframe_points: k.interpolation = "LINEAR"
# cheat light: the beam's spill on the boat while it passes (gaussian around frame 140)
cl = bpy.data.lights.new("BeamOnBoat", "SPOT"); cl.spot_size = math.radians(11); cl.spot_blend = 0.8; cl.color = (1, 0.9, 0.72)
clo = bpy.data.objects.new("BeamOnBoat", cl); sc.collection.objects.link(clo); clo.visible_volume_scatter = False
dvec = (Vector((BOATP.x, BOATP.y, 0)) - Vector((L.x, L.y, 0))).normalized()
clo.location = (L.x + 8 * dvec.x, L.y + 8 * dvec.y, top + 2.6)  # outside the lantern: the gallery floor would block it
tr = clo.constraints.new("TRACK_TO"); tgt = bpy.data.objects.new("BoatAim", None); sc.collection.objects.link(tgt)
tgt.location = (BOATP.x, BOATP.y, 2); tr.target = tgt; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
for f in range(LAMP_ON, 177):
    cl.energy = 2.5e6 * math.exp(-((f - 140) / 6.0) ** 2); cl.keyframe_insert("energy", frame=f)
if BOAT:
    boat(BOAT, oc, BOATP, math.radians(25))
# S1: three-quarter view of the point from the sea, lighthouse on the right third, slow push-in
camera("CamS1", [(1, Vector((-88, -98, 9))), (60, Vector((-81, -87, 9.6)))],
       [(1, Vector((-12, 48, 24))), (60, Vector((-11, 48, 24.5)))], 40)
# S4: low behind the boat, lighthouse upper left, beam sweeps toward camera across the boat
camera("CamS4", [(101, Vector((40, -36, 6.0))), (172, Vector((39, -34, 6.4)))],
       [(101, Vector((10, 18, 14.5))), (172, Vector((10, 19, 15))), ], 26)
render_settings()
sc.camera = bpy.data.objects["CamS1"]
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT, "ground z", round(gz, 2), "lamp z", round(top + 2.6, 2))
