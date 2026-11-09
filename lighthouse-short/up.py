"""4x-UltraSharp then Lanczos to 1920x1080 for every frame of a Wan clip (ComfyUI, chunks of 8 frames).

  python3 up.py <comfyui output prefix, e.g. lhw_s2_s7>  -> comfyui/output/up/<prefix>/<prefix>_*.png
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "webtoon-layers"))
from bench_cache import run  # noqa: E402
OUT = Path("/home/freshnel/dev/git/comfyui/output")
pre = sys.argv[1]
if Path(pre).is_dir():                      # a folder of frames (Blender renders)
    src = Path(pre).resolve(); pre = src.name; fs = sorted(src.glob("*.png"))
else:                                       # a ComfyUI output prefix
    src = OUT / "src" / pre
    src.mkdir(parents=True, exist_ok=True)
    fs = sorted(OUT.glob(f"{pre}_[0-9]*.png"))
    for f in fs:
        t = src / f.name
        if not t.exists(): t.symlink_to(f)
tot, CH = 0, 8
for k in range(0, len(fs), CH):
    g = {"1": {"class_type": "VHS_LoadImagesPath", "inputs": {"directory": str(src), "image_load_cap": CH, "skip_first_images": k, "select_every_nth": 1}},
         "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}},
         "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
         "4": {"class_type": "ImageScale", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "width": 1920, "height": 1080, "crop": "center"}},
         "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": f"up/{pre}/{pre}_{k:04d}"}}}
    r = run(g); tot += r["seconds"]
    if r["status"] != "success":
        print("error", k, json.dumps(r["error"])[:1500]); break
print(pre, len(fs), "frames", round(tot), "s", flush=True)
