"""Wan 2.2 5B Q8 video-to-video (SDEdit): encode a rendered sequence, re-noise to <denoise>, resample with a prompt.
Keeps the layout and motion of the Blender render, lets Wan add material detail (spray, clouds, textures).

  python3 v2v.py <name> <frames dir> "<prompt>" <denoise> [--seed N] [--frames 61] [--size 1024x576]
  -> comfyui/output/lhv_<name>_d<denoise>_*.png
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "webtoon-layers"))
from bench_cache import run  # noqa: E402
NEG = ("blurry, deformed, distorted, morphing, melting, static, frozen, worst quality, low quality, jpeg artifacts, "
       "watermark, text, subtitles, flicker")

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("dir"); ap.add_argument("prompt"); ap.add_argument("denoise", type=float)
ap.add_argument("--seed", type=int, default=7); ap.add_argument("--frames", type=int, default=61)
ap.add_argument("--size", default="1024x576"); ap.add_argument("--steps", type=int, default=20)
a = ap.parse_args()
w, h = [int(v) for v in a.size.split("x")]
g = {
    "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": a.prompt, "clip": ["2", 0]}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 0]}},
    "6": {"class_type": "VHS_LoadImagesPath", "inputs": {"directory": a.dir, "image_load_cap": a.frames, "skip_first_images": 0, "select_every_nth": 1}},
    "6b": {"class_type": "ImageScale", "inputs": {"image": ["6", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}},
    "7": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
    "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["6b", 0], "vae": ["3", 0]}},
    "9": {"class_type": "KSampler", "inputs": {"model": ["7", 0], "seed": a.seed, "steps": a.steps, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple",
                                               "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["8", 0], "denoise": a.denoise}},
    "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
    "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": f"lhv_{a.name}_d{int(a.denoise * 100)}"}},
}
r = run(g)
print(a.name, a.denoise, json.dumps({k: r[k] for k in ("status", "seconds")}), len(r["files"]), "files", flush=True)
if r["status"] == "error":
    print(json.dumps(r["error"])[:2000])
