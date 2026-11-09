"""Wan 2.2 TI2V 5B Q8 image-to-video, 16:9 (stdlib, ComfyUI on :8188).

  python3 wan.py <name> <image in comfyui/input> "<prompt>" [--seed N] [--frames 61] [--size 1024x576] [--steps 20]
  -> comfyui/output/lhw_<name>_*.png ; prints wall time
Settings from ../video-bench (uni_pc/simple, cfg 5, shift 8).
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "webtoon-layers"))
from bench_cache import run, wan_i2v  # noqa: E402

NEG = ("blurry, deformed face, distorted face, morphing, melting, static, frozen, worst quality, low quality, jpeg artifacts, "
       "watermark, text, subtitles, extra limbs, extra fingers, flicker")
ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("image"); ap.add_argument("prompt")
ap.add_argument("--seed", type=int, default=7); ap.add_argument("--frames", type=int, default=61)
ap.add_argument("--size", default="1024x576"); ap.add_argument("--steps", type=int, default=20)
a = ap.parse_args()
g = wan_i2v(a.seed, a.frames, f"lhw_{a.name}")
g["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}}
g["4"]["inputs"]["text"] = a.prompt
g["5"]["inputs"]["text"] = NEG
g["6"]["inputs"]["image"] = a.image
g["9"]["inputs"]["steps"] = a.steps
w, h = [int(v) for v in a.size.split("x")]
g["8"]["inputs"].update(width=w, height=h)
r = run(g)
print(a.name, json.dumps({k: r[k] for k in ("status", "seconds")}), len(r["files"]), "files", flush=True)
if r["status"] == "error":
    print(json.dumps(r["error"])[:2000])
