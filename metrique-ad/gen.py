"""ComfyUI API client for the MÉTRIQUE ad shots (stdlib only).

Usage:
  python3 gen.py kf P03 [P04 ...] [--seeds 4]        # Wan T2I keyframes -> assets/keyframes/
  python3 gen.py i2v P03 P04 ... [--seed N] [--frames N]   # keyframes from selected.json
"""
import argparse, json, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

from shots import SHOTS, NEG_WAN, NEG_LTX

API = "http://127.0.0.1:8188"
COMFY = Path("/home/freshnel/dev/git/comfyui")
ROOT = Path(__file__).resolve().parent
W, H = 480, 832


def wan_graph(prompt, neg, seed, frames, prefix, image=None):
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "ms": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["unet", 0], "shift": 8}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": neg}},
        "lat": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["vae", 0], "width": W, "height": H, "length": frames, "batch_size": 1}},
        "ks": {"class_type": "KSampler", "inputs": {"model": ["ms", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["lat", 0],
                                                    "seed": seed, "steps": 20, "cfg": 5, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": prefix}},
    }
    if image:
        g["img"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        g["lat"]["inputs"]["start_image"] = ["img", 0]
    return g


def ltx_graph(prompt, neg, seed, frames, prefix, image):
    return {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ltxv-2b-0.9.8-distilled-fp8.safetensors"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5xxl_fp8_e4m3fn.safetensors", "type": "ltxv", "device": "default"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": neg}},
        "img": {"class_type": "LoadImage", "inputs": {"image": image}},
        "i2v": {"class_type": "LTXVImgToVideo", "inputs": {"positive": ["pos", 0], "negative": ["neg", 0], "vae": ["ckpt", 2], "image": ["img", 0],
                                                           "width": 512, "height": 896, "length": frames, "batch_size": 1, "strength": 1.0}},
        "cond": {"class_type": "LTXVConditioning", "inputs": {"positive": ["i2v", 0], "negative": ["i2v", 1], "frame_rate": 24}},
        "sched": {"class_type": "LTXVScheduler", "inputs": {"steps": 8, "max_shift": 2.05, "base_shift": 0.95, "stretch": True, "terminal": 0.1, "latent": ["i2v", 2]}},
        "smp": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "sc": {"class_type": "SamplerCustom", "inputs": {"model": ["ckpt", 0], "add_noise": True, "noise_seed": seed, "cfg": 1.0, "positive": ["cond", 0],
                                                        "negative": ["cond", 1], "sampler": ["smp", 0], "sigmas": ["sched", 0], "latent_image": ["i2v", 2]}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["sc", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": prefix}},
    }


def with_rife(g):
    """Insert RIFE x2 between decode and save: 24 fps -> 48 fps (resampled to 30 fps in upscale.py)."""
    g["rife"] = {"class_type": "RIFE VFI", "inputs": {"ckpt_name": "rife47.pth", "frames": ["dec", 0], "clear_cache_after_n_frames": 10,
                                                    "multiplier": 2, "fast_mode": True, "ensemble": True, "scale_factor": 1.0,
                                                    "dtype": "float32", "torch_compile": False, "batch_size": 1}}
    g["save"]["inputs"]["images"] = ["rife", 0]
    return g


def run(graph):
    req = urllib.request.Request(f"{API}/prompt", data=json.dumps({"prompt": graph}).encode(), headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(3)
        h = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
        if pid in h:
            entry = h[pid]
            if entry.get("status", {}).get("status_str") == "error":
                sys.exit(f"ComfyUI error: {json.dumps(entry['status'])[:2000]}")
            imgs = [i for o in entry["outputs"].values() for i in o.get("images", [])]
            return [COMFY / "output" / i["subfolder"] / i["filename"] for i in imgs], time.time() - t0


def log(line):
    print(line, flush=True)
    with open(ROOT / "gen.log", "a") as f:
        f.write(line + "\n")


def keyframes(names, n, off=0):
    # One graph per shot: all seeds share a single model load (ComfyUI runs with --cache-none).
    out = ROOT / "assets/keyframes"
    for name in names:
        s = SHOTS[name]
        seeds = [s["seed"] * 10 + k + off for k in range(n)]
        g = wan_graph(s["prompt"], NEG_WAN + s.get("neg_extra", ""), seeds[0], 1, f"metrique/{name}_kf_{seeds[0]}")
        for seed in seeds[1:]:
            g[f"ks{seed}"] = {"class_type": "KSampler", "inputs": dict(g["ks"]["inputs"], seed=seed)}
            g[f"dec{seed}"] = {"class_type": "VAEDecode", "inputs": {"samples": [f"ks{seed}", 0], "vae": ["vae", 0]}}
            g[f"save{seed}"] = {"class_type": "SaveImage", "inputs": {"images": [f"dec{seed}", 0], "filename_prefix": f"metrique/{name}_kf_{seed}"}}
        files, dt = run(g)
        for seed in seeds:
            f = next(f for f in files if f.name.startswith(f"{name}_kf_{seed}_"))
            shutil.copy(f, out / f"{name}_{seed}.png")
        log(f"kf {name} seeds={seeds} {dt:.0f}s")


SHARED = {"unet", "clip", "vae", "ms", "ckpt"}


def merge(graphs):
    """Merge per-shot graphs into one so the shared loaders run once (ComfyUI runs with --cache-none)."""
    out = {}
    for tag, g in graphs:
        ren = {k: (k if k in SHARED else f"{k}_{tag}") for k in g}
        for k, node in g.items():
            inputs = {n: ([ren[v[0]], v[1]] if isinstance(v, list) and len(v) == 2 and v[0] in ren else v)
                      for n, v in node["inputs"].items()}
            out[ren[k]] = {"class_type": node["class_type"], "inputs": inputs}
    return out


def i2v(names, seed_override=None, frames_override=None):
    """Render several shots in one graph per model; keyframes come from selected.json."""
    sel = json.loads((ROOT / "selected.json").read_text())
    jobs = {"wan": [], "ltx": []}
    for name in names:
        s = SHOTS[name]
        seed = seed_override or s["seed"]
        frames = frames_override or s["frames"]
        key = (ROOT / sel[name]["key"]).resolve()
        shutil.copy(key, COMFY / "input" / key.name)
        prefix = f"metrique/{name}_v{seed}"
        if s["model"] == "ltx":
            g = ltx_graph(s["prompt"], NEG_LTX, seed, frames, prefix, key.name)
        else:
            g = wan_graph(s["prompt"], NEG_WAN + s.get("neg_extra", ""), seed, frames, prefix, key.name)
        jobs[s["model"]].append((name, seed, frames, key.name, with_rife(g)))
    for model, items in jobs.items():
        if not items:
            continue
        files, dt = run(merge([(n, g) for n, _, _, _, g in items]))
        for name, seed, frames, key, _ in items:
            dst = ROOT / "clips" / f"{name}_{seed}"
            if dst.exists():
                shutil.rmtree(dst)
            dst.mkdir(parents=True)
            mine = sorted(f for f in files if f.name.startswith(f"{name}_v{seed}_"))
            for i, f in enumerate(mine):
                shutil.copy(f, dst / f"{i:04d}.png")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "48", "-i", str(dst / "%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dst.with_suffix(".mp4"))], check=True)
            log(f"i2v {name} model={model} seed={seed} frames={frames} key={key} out={len(mine)}f")
        log(f"i2v batch {model} {[i[0] for i in items]} {dt:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["kf", "i2v"])
    ap.add_argument("shots", nargs="+")
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--seed-offset", type=int, default=0)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--frames", type=int)
    a = ap.parse_args()
    if a.mode == "kf":
        keyframes(a.shots, a.seeds, a.seed_offset)
    else:
        i2v(a.shots, a.seed, a.frames)
