"""Render frames of the lighthouse set with Cycles.

  blender -b <scene.blend> --python render.py -- <camera> <f0> <f1> <outdir> [pct=100] [samples=64] [GPU|CPU] [step=1]
-> <outdir>/<camera>_<frame>.png ; prints seconds per frame.
"""
import sys, time, bpy
a = sys.argv[sys.argv.index("--") + 1:]
cam, f0, f1, out = a[0], int(a[1]), int(a[2]), a[3]
size = a[4] if len(a) > 4 else "100"
spp = int(a[5]) if len(a) > 5 else 64
dev = a[6] if len(a) > 6 else "GPU"
step = int(a[7]) if len(a) > 7 else 1
sc = bpy.context.scene
sc.render.engine = "CYCLES"
c = sc.cycles
if dev == "GPU":
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "CUDA"; p.get_devices()
    for d in p.devices: d.use = d.type == "CUDA"
    c.device = "GPU"
else:
    c.device = "CPU"
c.samples = spp
c.use_denoising = True
c.denoiser = "OPENIMAGEDENOISE"
c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02
c.max_bounces = 6; c.volume_bounces = 1; c.transparent_max_bounces = 8; c.transmission_bounces = 4
c.volume_step_rate = 4.0; c.volume_preview_step_rate = 8.0; c.volume_max_steps = 256
c.caustics_reflective = c.caustics_refractive = False
c.blur_glossy = 1.0
if "x" in size:
    sc.render.resolution_x, sc.render.resolution_y = map(int, size.split("x")); sc.render.resolution_percentage = 100
else:
    sc.render.resolution_percentage = int(size)
sc.render.use_persistent_data = True
sc.camera = bpy.data.objects[cam]
for f in range(f0, f1 + 1, step):
    sc.frame_set(f)
    sc.render.filepath = f"{out}/{cam}_{f:04d}.png"
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {cam} {f} {time.time() - t0:.1f}s", flush=True)
