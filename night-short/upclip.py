"""x2 anime upscale of every frame of a clip through ComfyUI: python3 upclip.py <comfyui output prefix>  -> <prefix>_x2/ in comfyui/output"""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, "../webtoon-layers")
from bench_cache import run
OUT, IN = Path("../comfyui/output"), Path("../comfyui/input")
pre = sys.argv[1]
fs = sorted(OUT.glob(f"{pre}_[0-9]*.png"))
tot = 0
for i, f in enumerate(fs):
    shutil.copy(f, IN / f"upsrc_{pre}.png")
    g = {"1": {"class_type": "LoadImage", "inputs": {"image": f"upsrc_{pre}.png"}},
         "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "RealESRGAN_x4plus_anime_6B.pth"}},
         "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
         "4": {"class_type": "ImageScaleBy", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "scale_by": 0.5}},
         "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": f"x2/{pre}_{i:04d}"}}}
    r = run(g); tot += r["seconds"]
    if r["status"] != "success": print("error", i, r["error"]); break
print(pre, len(fs), "frames", round(tot), "s")
