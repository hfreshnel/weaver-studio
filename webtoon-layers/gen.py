"""Generate webtoon layers through a running ComfyUI (stdlib only).

  python3 gen.py kf <shot> [--seed N] [--batch 3]          # Animagine keyframes on green -> comfyui/output/kf_<shot>_*
  python3 gen.py i2v <shot> <image> [--seed N] [--frames 49]   # Wan 5B Q8 I2V from comfyui/input/<image> -> comfyui/output/i2v_<shot>_*

Shots are defined in SHOTS: static camera, the character really moves inside the frame, so her feet stay planted
on the (invisible) ground and the composite needs no fake camera move.
"""
import argparse, json

from bench_cache import CHAR_NEG, WALK_NEG, animagine, run, wan_i2v

CHAR_BASE = ("1girl, solo, short black hair, bob cut, amber eyes, red hair ribbon, white sailor uniform, navy blue collar, "
             "small mole under left eye, white socks, black loafers")
GREEN = "simple background, green background, solid green background, flat green background, chroma key"
STYLE = "webtoon style, clean lineart, flat colors, masterpiece, high score, great score, absurdres"

SHOTS = {
    # Walks toward the static camera: starts small, mid-frame, lots of headroom so she can grow without being cut.
    "front": dict(
        # Keyframe: the original green_girl.png shrunk to 55 % on a padded green canvas (front_pad.png): same character,
        # room to grow. "small figure, wide shot, distant" prompts changed the drawing style and the outfit.
        kf=f"{CHAR_BASE}, full body, standing, walking pose, from front, {GREEN}, {STYLE}",
        i2v="the girl walks slowly straight towards the camera with a calm natural walking cycle, she gets gradually closer, arms "
            "swinging gently, hair and skirt moving, static camera, solid green background stays flat and unchanged, anime style",
    ),
    # Walks across the frame in profile, left to right, static camera.
    "side": dict(
        kf=f"{CHAR_BASE}, full body, standing, walking pose, from side, profile, facing right, {GREEN}, {STYLE}",
        i2v="the girl walks in profile across the whole frame, from the left edge to the right edge, she keeps moving forward to "
            "the right at a steady pace with a natural walking cycle, arms swinging, static camera, solid green background stays "
            "flat and unchanged, anime style",
    ),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["kf", "i2v"])
    ap.add_argument("shot", choices=SHOTS)
    ap.add_argument("image", nargs="?")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--batch", type=int, default=3)
    ap.add_argument("--frames", type=int, default=49)
    args = ap.parse_args()
    shot = SHOTS[args.shot]
    if args.mode == "kf":
        g = animagine(shot["kf"], CHAR_NEG, args.seed, f"kf_{args.shot}")
        g["4"]["inputs"]["batch_size"] = args.batch
    else:
        g = wan_i2v(args.seed, args.frames, f"i2v_{args.shot}_s{args.seed}")
        g["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}}
        g["4"]["inputs"]["text"] = shot["i2v"]
        g["5"]["inputs"]["text"] = WALK_NEG
        g["6"]["inputs"]["image"] = args.image
    r = run(g)
    print(json.dumps({k: r[k] for k in ("status", "seconds")}), len(r["files"]), "files", r["files"][:3])
    if r["status"] == "error":
        print(json.dumps(r["error"])[:3000])


if __name__ == "__main__":
    main()
