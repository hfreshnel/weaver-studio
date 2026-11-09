"""Animagine keyframes on green for the night short (stdlib, needs ComfyUI on :8188).

  python3 kf.py <shot> [--seed N] [--batch 4]     # -> comfyui/output/ns_kf_<shot>_*
"""
import argparse, json, sys
sys.path.insert(0, "../webtoon-layers")
from bench_cache import CHAR_NEG, animagine, run

BASE = ("1girl, solo, short black hair, bob cut, amber eyes, red hair ribbon, white sailor uniform, navy blue collar, "
        "small mole under left eye")
GREEN = "simple background, green background, solid green background, flat green background, chroma key"
STYLE = "webtoon style, clean lineart, flat colors, masterpiece, high score, great score, absurdres"
SHOTS = {
    "side": f"1girl, solo, short black hair, bob cut, amber eyes, red hair ribbon, white sailor uniform, navy blue sailor collar, short sleeves, white pleated skirt, white socks, black loafers, full body, from side, profile, facing right, walking pose, {GREEN}, {STYLE}",
    "front": f"1girl, solo, short black hair, bob cut, amber eyes, red hair ribbon, white sailor uniform, navy blue sailor collar, short sleeves, white pleated skirt, white socks, black loafers, small mole under left eye, full body, standing, from front, looking at viewer, walking pose, {GREEN}, {STYLE}",
    "mid": f"{BASE}, white socks, black loafers, cowboy shot, standing, from front, looking up, face turned up, smile, hands at sides, skirt, {GREEN}, {STYLE}",
    "close": f"{BASE}, portrait, close-up, face focus, upper body, looking at viewer, gentle smile, hands out of frame, {GREEN}, {STYLE}",
    "back": f"1girl, solo, short black hair, bob cut, red hair ribbon, white sailor uniform, navy blue sailor collar, white socks, black loafers, full body, standing, from behind, facing away, back focus, straight on, symmetrical, walking pose, {GREEN}, {STYLE}",
}
ap = argparse.ArgumentParser()
ap.add_argument("shot", choices=SHOTS)
ap.add_argument("--seed", type=int, default=21)
ap.add_argument("--batch", type=int, default=4)
a = ap.parse_args()
neg = CHAR_NEG + (", looking back, looking at viewer, from side, profile, face, three-quarter view" if a.shot == "back" else ", looking at viewer, from front, from behind, three-quarter view" if a.shot == "side" else "")
g = animagine(SHOTS[a.shot], neg, a.seed, f"ns_kf_{a.shot}{a.seed}")
g["4"]["inputs"]["batch_size"] = a.batch
r = run(g)
print(json.dumps({k: r[k] for k in ("status", "seconds")}), r["files"])
