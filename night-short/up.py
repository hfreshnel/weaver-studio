"""RealESRGAN anime 6B x4 then Lanczos back to x2 through ComfyUI. python3 up.py <input image> <prefix>"""
import json, sys
sys.path.insert(0, "../webtoon-layers")
from bench_cache import run
g = {"1": {"class_type": "LoadImage", "inputs": {"image": sys.argv[1]}},
     "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "RealESRGAN_x4plus_anime_6B.pth"}},
     "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
     "4": {"class_type": "ImageScaleBy", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "scale_by": 0.5}},
     "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": sys.argv[2]}}}
r = run(g); print(json.dumps({k: r[k] for k in ("status", "seconds", "files")}), r.get("error"))
