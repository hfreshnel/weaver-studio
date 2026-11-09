"""Wan 2.2 5B Q8 I2V job (stdlib, ComfyUI on :8188).

  python3 w.py <name> <image in comfyui/input> "<prompt>" [--seed N] [--frames 49]  -> comfyui/output/ns_<name>_*
"""
import argparse, json, sys
sys.path.insert(0, "../webtoon-layers")
from bench_cache import WALK_NEG, run, wan_i2v

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("image"); ap.add_argument("prompt")
ap.add_argument("--seed", type=int, default=11); ap.add_argument("--frames", type=int, default=49)
ap.add_argument("--neg", default=WALK_NEG); ap.add_argument("--size", default="512x752")
a = ap.parse_args()
g = wan_i2v(a.seed, a.frames, f"ns_{a.name}")
g["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}}
g["4"]["inputs"]["text"] = a.prompt
g["5"]["inputs"]["text"] = a.neg
g["6"]["inputs"]["image"] = a.image
w_, h_ = [int(v) for v in a.size.split("x")]; g["8"]["inputs"]["width"], g["8"]["inputs"]["height"] = w_, h_
r = run(g)
print(json.dumps({k: r[k] for k in ("status", "seconds")}), len(r["files"]), "files")
if r["status"] == "error": print(json.dumps(r["error"])[:2000])
