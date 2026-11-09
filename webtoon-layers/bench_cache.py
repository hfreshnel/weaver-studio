"""Replay a typical webtoon session against a running ComfyUI and time each job (stdlib only).

Usage: python3 bench_cache.py <label>
Writes bench/<label>.json (per-job wall time + output files).
"""
import json, sys, time, urllib.request
from pathlib import Path

API = "http://127.0.0.1:8188"
ROOT = Path(__file__).resolve().parent

CHAR = ("1girl, short black hair, bob cut, amber eyes, red hair ribbon, white sailor uniform, navy blue collar, small mole under left eye, "
        "full body, standing, walking pose, from front, simple background, green background, solid green background, flat green background, "
        "chroma key, webtoon style, clean lineart, flat colors, masterpiece, high score, great score, absurdres")
CHAR_NEG = ("lowres, bad anatomy, bad hands, text, error, worst quality, low quality, blurry, watermark, extra fingers, gradient background, "
            "shadow on background, scenery, building, sky, floor")
DECOR = ("no humans, scenery, japanese residential street, cherry blossom trees, utility poles, sunny day, eye level, wide street, empty street, "
         "webtoon style, clean lineart, flat colors, masterpiece, high score, great score, absurdres")
DECOR_NEG = "lowres, text, error, worst quality, low quality, blurry, watermark, 1girl, 1boy, person, people, character"
WALK = ("the girl walks forward in place with a gentle walking cycle, arms swinging naturally, hair and skirt moving slightly, "
        "solid green background stays flat and unchanged, static camera, anime style")
WALK_NEG = "blurry, static, worst quality, deformed, extra limbs, jittery, watermark, text"


def animagine(prompt, neg, seed, prefix):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
                                                   "seed": seed, "steps": 25, "cfg": 5.0, "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": prefix}},
    }


def wan_i2v(seed, frames, prefix):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": WALK, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": WALK_NEG, "clip": ["2", 0]}},
        "6": {"class_type": "LoadImage", "inputs": {"image": "green_girl.png"}},
        "7": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "8": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["3", 0], "start_image": ["6", 0], "width": 512, "height": 752,
                                                                   "length": frames, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {"model": ["7", 0], "seed": seed, "steps": 20, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple",
                                                   "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["8", 0], "denoise": 1.0}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
    }


def run(graph):
    req = urllib.request.Request(f"{API}/prompt", data=json.dumps({"prompt": graph}).encode(), headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(1)
        h = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            imgs = [i["filename"] for o in h[pid]["outputs"].values() for i in o.get("images", [])]
            return {"status": st.get("status_str"), "seconds": round(time.time() - t0, 1), "files": imgs,
                    "error": None if st.get("status_str") != "error" else st.get("messages")}


def main():
    label = sys.argv[1]
    p = f"bench_{label}/"
    jobs = [
        ("anim_char_s1", animagine(CHAR, CHAR_NEG, 1, p + "char_s1")),
        ("anim_char_s2", animagine(CHAR, CHAR_NEG, 2, p + "char_s2")),
        ("anim_decor_s3", animagine(DECOR, DECOR_NEG, 3, p + "decor_s3")),
        ("wan_s7", wan_i2v(7, 25, p + "wan_s7")),
        ("wan_s8", wan_i2v(8, 25, p + "wan_s8")),
        ("anim_char_s4", animagine(CHAR, CHAR_NEG, 4, p + "char_s4")),
    ]
    out = ROOT / "bench" / f"{label}.json"
    out.parent.mkdir(exist_ok=True)
    results = []
    for name, g in jobs:
        r = run(g)
        r["job"], r["t_end"] = name, round(time.time(), 1)
        results.append(r)
        print(f"{name:15s} {r['status']:8s} {r['seconds']:7.1f} s", flush=True)
        out.write_text(json.dumps(results, indent=1))
        if r["status"] == "error":
            break


if __name__ == "__main__":
    main()
