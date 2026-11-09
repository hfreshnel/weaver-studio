"""Style ladder: same scene, 8 styles from flat cartoon to photo, across several image models (stdlib only).

Usage:
  python3 gen.py <model> [<model> ...] [--styles flat,anime,...] [--seeds 101,202]
Models: animagine, juggernaut, zimage, klein, wan. Outputs -> out/<model>/<style>_s<seed>.png, timings -> gen.log
"""
import argparse, json, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path

API = "http://127.0.0.1:8188"
COMFY = Path("/home/freshnel/dev/git/comfyui")
ROOT = Path(__file__).resolve().parent

SUBJECT = ("a young woman with short black bob hair and a red jacket sits at a small round table on a café terrace, "
           "holding a white coffee cup with both hands and smiling, a cobblestone street with trees and parked bicycles "
           "behind her, warm late afternoon sunlight, medium shot")
SUBJECT_TAGS = ("1girl, solo, short hair, black hair, bob cut, red jacket, sitting, cafe, outdoors, table, holding cup, "
                "coffee cup, smile, street, tree, bicycle, sunlight, upper body")

# Ordered from full cartoon to photorealism. (natural-language prefix, Animagine tags or None = skipped for Animagine)
STYLES = {
    "1_flat": ("Flat 2D cartoon illustration with thick black outlines, simple geometric shapes, flat bright colors and no shading, "
               "in the style of a modern children's TV cartoon.", "flat color, no shading, thick outlines, cartoon"),
    "2_anime": ("Anime illustration, webtoon style, clean thin lineart, cel shading, vibrant colors.", "anime coloring, cel shading"),
    "3_bd": ("European comic book panel, ligne claire style, clean uniform ink outlines, flat colors, detailed background.",
             "western comics (style), ligne claire, flat color"),
    "4_3d": ("3D animated feature film still, stylized cartoon character with big expressive eyes and soft rounded shapes, "
             "global illumination, subsurface scattering, high-quality 3D render.", "3d, blender (medium)"),
    "5_paint": ("Digital painting, concept art, visible painterly brush strokes, rich colors, soft edges.", "painterly, impasto, realistic"),
    "6_semi": ("Semi-realistic digital illustration, realistic proportions and detailed rendering with a soft painted finish.", None),
    "7_cine": ("Cinematic film still shot on 35mm film, natural film grain, shallow depth of field, color graded.", None),
    "8_photo": ("Professional photograph taken with a DSLR and an 85mm lens, natural skin texture, sharp focus, photorealistic.", None),
    # 8_photo made Z-Image put a camera on the table: same intent without naming the device.
    "9_photo2": ("Natural-light portrait photograph, shallow depth of field, natural skin texture, sharp focus, photorealistic.", None),
}

NEG = "lowres, blurry, bad anatomy, bad hands, extra fingers, deformed face, watermark, text, signature"
NEG_ANIM = ("lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, "
            "low quality, low score, bad score, average score, signature, watermark, username, blurry")
QUALITY_ANIM = "masterpiece, high score, great score, absurdres"


def prompt_for(model, style):
    text, tags = STYLES[style]
    if model == "animagine":
        return f"{SUBJECT_TAGS}, {tags}, {QUALITY_ANIM}" if tags else None
    return f"{text} {SUBJECT[0].upper()}{SUBJECT[1:]}."


# Each builder returns (shared loader nodes, function(seed, tag) -> per-image nodes ending in a SaveImage).
def animagine(prompt, prefix):
    g = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["ckpt", 1], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["ckpt", 1], "text": NEG_ANIM}},
        "lat": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    }
    ks = dict(model=["ckpt", 0], positive=["pos", 0], negative=["neg", 0], latent_image=["lat", 0],
              steps=25, cfg=5, sampler_name="euler_ancestral", scheduler="normal", denoise=1)
    return g, lambda s: ksampler_tail(ks, s, ["ckpt", 2], prefix)


def juggernaut(prompt, prefix):
    g = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["ckpt", 1], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["ckpt", 1], "text": NEG}},
        "lat": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    }
    ks = dict(model=["ckpt", 0], positive=["pos", 0], negative=["neg", 0], latent_image=["lat", 0],
              steps=30, cfg=4.5, sampler_name="dpmpp_2m", scheduler="karras", denoise=1)
    return g, lambda s: ksampler_tail(ks, s, ["ckpt", 2], prefix)


def zimage(prompt, prefix):
    g = {
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "z-image-turbo-Q5_K_M.gguf"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b_fp8_mixed.safetensors", "type": "lumina2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "ms": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["unet", 0], "shift": 3}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": ""}},
        "lat": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    }
    ks = dict(model=["ms", 0], positive=["pos", 0], negative=["neg", 0], latent_image=["lat", 0],
              steps=8, cfg=1, sampler_name="res_multistep", scheduler="simple", denoise=1)
    return g, lambda s: ksampler_tail(ks, s, ["vae", 0], prefix)


def klein(prompt, prefix):
    g = {
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux-2-klein-4b-Q8_0.gguf"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b_fp8_mixed.safetensors", "type": "flux2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["pos", 0]}},
        "guider": {"class_type": "CFGGuider", "inputs": {"model": ["unet", 0], "positive": ["pos", 0], "negative": ["neg", 0], "cfg": 1}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "sigmas": {"class_type": "Flux2Scheduler", "inputs": {"steps": 4, "width": 832, "height": 1216}},
        "lat": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    }

    def tail(s):
        return {
            f"noise{s}": {"class_type": "RandomNoise", "inputs": {"noise_seed": s}},
            f"sca{s}": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": [f"noise{s}", 0], "guider": ["guider", 0], "sampler": ["sampler", 0],
                                                                          "sigmas": ["sigmas", 0], "latent_image": ["lat", 0]}},
            f"dec{s}": {"class_type": "VAEDecode", "inputs": {"samples": [f"sca{s}", 0], "vae": ["vae", 0]}},
            f"save{s}": {"class_type": "SaveImage", "inputs": {"images": [f"dec{s}", 0], "filename_prefix": f"{prefix}_s{s}"}},
        }
    return g, tail


def wan(prompt, prefix):
    g = {
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "ms": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["unet", 0], "shift": 8}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": NEG}},
        "lat": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["vae", 0], "width": 704, "height": 1280, "length": 1, "batch_size": 1}},
    }
    ks = dict(model=["ms", 0], positive=["pos", 0], negative=["neg", 0], latent_image=["lat", 0],
              steps=20, cfg=5, sampler_name="uni_pc", scheduler="simple", denoise=1)
    return g, lambda s: ksampler_tail(ks, s, ["vae", 0], prefix)


def ksampler_tail(ks, s, vae, prefix):
    return {
        f"ks{s}": {"class_type": "KSampler", "inputs": dict(ks, seed=s)},
        f"dec{s}": {"class_type": "VAEDecode", "inputs": {"samples": [f"ks{s}", 0], "vae": vae}},
        f"save{s}": {"class_type": "SaveImage", "inputs": {"images": [f"dec{s}", 0], "filename_prefix": f"{prefix}_s{s}"}},
    }


MODELS = {"animagine": animagine, "juggernaut": juggernaut, "zimage": zimage, "klein": klein, "wan": wan}


class Peak:
    """Sample VRAM used, system RAM used and swap used every second; keep the max."""
    def __init__(self):
        self.vram = self.ram = self.swap = 0
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._stop.is_set():
            v = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
            m = dict(l.split(":") for l in Path("/proc/meminfo").read_text().splitlines())
            kb = lambda k: int(m[k].split()[0])
            self.vram = max(self.vram, int(v.strip() or 0))
            self.ram = max(self.ram, (kb("MemTotal") - kb("MemAvailable")) // 1024)
            self.swap = max(self.swap, (kb("SwapTotal") - kb("SwapFree")) // 1024)
            time.sleep(1)

    def stop(self):
        self._stop.set()
        return f"vram={self.vram}MiB ram={self.ram / 1024:.1f}G swap={self.swap / 1024:.1f}G"


def run(graph):
    req = urllib.request.Request(f"{API}/prompt", data=json.dumps({"prompt": graph}).encode(), headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(1)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+", choices=list(MODELS))
    ap.add_argument("--styles", default=",".join(STYLES))
    ap.add_argument("--seeds", default="101,202")
    # Grouped decode is the default: bit-identical images, -16 % per image on Z-Image (see NOTES.md).
    ap.add_argument("--per-seed-decode", dest="group_decode", action="store_false",
                    help="decode each seed right after sampling (old behaviour: the model is unloaded between seeds)")
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    for model in a.models:
        label = model
        out = ROOT / "out" / label
        out.mkdir(parents=True, exist_ok=True)
        for style in a.styles.split(","):
            prompt = prompt_for(model, style)
            if prompt is None:
                continue
            # One job per (model, style): seeds share the text encoding; models stay cached between jobs.
            prefix = f"styles/{label}_{style}"
            g, tail = MODELS[model](prompt, prefix)
            for s in seeds:
                g.update(tail(s))
            if a.group_decode:
                group_decode(g, seeds, prefix)
            peak = Peak()
            files, dt = run(g)
            mem = peak.stop()
            if a.group_decode:
                # The batch keeps seed order; SaveImage numbers its images in that order.
                for s, f in zip(seeds, sorted(files)):
                    shutil.copy(f, out / f"{style}_s{s}.png")
            else:
                for s in seeds:
                    f = next(f for f in files if f.name.startswith(f"{label}_{style}_s{s}_"))
                    shutil.copy(f, out / f"{style}_s{s}.png")
            log(f"{time.strftime('%H:%M:%S')} {label} {style} seeds={seeds} {dt:.0f}s ({dt / len(seeds):.0f}s/img) {mem}")


def group_decode(g, seeds, prefix):
    """Replace the per-seed decode/save nodes with LatentBatch -> one VAEDecode -> one SaveImage."""
    latents, vae = [], None
    for s in seeds:
        dec = g.pop(f"dec{s}")
        g.pop(f"save{s}")
        latents.append(dec["inputs"]["samples"])
        vae = dec["inputs"]["vae"]
    src = latents[0]
    for i, lat in enumerate(latents[1:]):
        g[f"batch{i}"] = {"class_type": "LatentBatch", "inputs": {"samples1": src, "samples2": lat}}
        src = [f"batch{i}", 0]
    g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": src, "vae": vae}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": prefix}}


if __name__ == "__main__":
    main()
