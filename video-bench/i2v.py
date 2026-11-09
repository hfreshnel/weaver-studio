"""Block B: Wan 2.2 5B Q8 I2V from the keyframes of kf.py, several clips in ONE graph (models load once with --cache-none).

Usage: python3 i2v.py <model>:<prompt> [...] [--frames 49] [--seed 7]     e.g. i2v.py zimage:portrait wan:portrait
Outputs -> clips/<model>_<prompt>/ (PNG frames, 24 fps), timings -> i2v.log.
"""
import argparse, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "style-ladder"))
import gen as sl  # noqa: E402

ROOT = Path(__file__).resolve().parent
W, H = 480, 832
MOTION = {
    "portrait": "the young woman smiles softly and blinks naturally, her hair and jacket move slightly in a light breeze, subtle head movement, static camera",
    "walk": "the young woman walks forward along the street with a natural walking cycle, arms swinging gently, static camera",
    "anime": "the girl walks forward along the street with a natural walking cycle, hair moving, anime style, static camera",
}
NEG = "blurry, static, worst quality, deformed, extra limbs, jittery, watermark, text"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--frames", type=int, default=49)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    g = {
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "ms": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["unet", 0], "shift": 8}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": NEG}},
    }
    prefixes = {}
    for plan in a.plans:
        model, name = plan.split(":")
        src = ROOT / "kf" / model / f"{name}_s101.png"
        dst = sl.COMFY / "input" / f"vb_{model}_{name}.png"
        shutil.copy(src, dst)
        k = f"{model}_{name}"
        prefixes[k] = f"vb_clips/{k}"
        g.update({
            f"img_{k}": {"class_type": "LoadImage", "inputs": {"image": dst.name}},
            f"sc_{k}": {"class_type": "ImageScale", "inputs": {"image": [f"img_{k}", 0], "upscale_method": "lanczos", "width": W, "height": H, "crop": "center"}},
            f"pos_{k}": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": MOTION[name]}},
            f"lat_{k}": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["vae", 0], "start_image": [f"sc_{k}", 0], "width": W, "height": H, "length": a.frames, "batch_size": 1}},
            f"ks_{k}": {"class_type": "KSampler", "inputs": {"model": ["ms", 0], "positive": [f"pos_{k}", 0], "negative": ["neg", 0], "latent_image": [f"lat_{k}", 0],
                                                            "seed": a.seed, "steps": 20, "cfg": 5, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1}},
            f"dec_{k}": {"class_type": "VAEDecode", "inputs": {"samples": [f"ks_{k}", 0], "vae": ["vae", 0]}},
            f"save_{k}": {"class_type": "SaveImage", "inputs": {"images": [f"dec_{k}", 0], "filename_prefix": prefixes[k]}},
        })
    peak = sl.Peak()
    files, dt = sl.run(g)
    mem = peak.stop()
    for k, p in prefixes.items():
        out = ROOT / "clips" / k
        out.mkdir(parents=True, exist_ok=True)
        for f in sorted(x for x in files if x.parent.name == "vb_clips" and x.name.startswith(Path(p).name + "_")):
            shutil.copy(f, out / f.name)
    line = f"{time.strftime('%H:%M:%S')} i2v {a.plans} frames={a.frames} {dt:.0f}s ({dt / len(a.plans):.0f}s/clip) {mem}"
    print(line, flush=True)
    with open(ROOT / "i2v.log", "a") as f:
        f.write(line + "\n")


if __name__ == "__main__":
    main()
