"""Blender headless GPU check: renders a cube with EEVEE and Cycles (CUDA/OptiX), prints timings.
  blender -b --factory-startup --python gputest.py -- <outdir>"""
import sys, time, bpy
out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 640, 360
print("ENGINES", [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items])
for eng in ("BLENDER_EEVEE", "CYCLES"):
    sc.render.engine = eng
    if eng == "CYCLES":
        p = bpy.context.preferences.addons["cycles"].preferences
        for t in ("OPTIX", "CUDA"):
            try:
                p.compute_device_type = t; p.get_devices()
                devs = [d for d in p.devices if d.type == t]
                if devs:
                    for d in p.devices: d.use = d.type == t
                    print("CYCLES DEVICE", t, [d.name for d in devs]); break
            except Exception as e: print("no", t, e)
        sc.cycles.device = "GPU"; sc.cycles.samples = 32
    sc.render.filepath = f"{out}/gputest_{eng}.png"
    t0 = time.time()
    try:
        bpy.ops.render.render(write_still=True); print("RENDER", eng, "OK", round(time.time() - t0, 2), "s")
    except Exception as e: print("RENDER", eng, "FAIL", e)
