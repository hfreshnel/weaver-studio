"""Block A: keyframes for the I2V tests, same prompts/seed across image models (reuses style-ladder builders).

Usage: python3 kf.py <model> [<model> ...] [--seeds 101]      models: wan, zimage, klein
Outputs -> kf/<model>/<prompt>_s<seed>.png, timings -> kf.log. Size 608x1056 (ratio of the 480x832 I2V input).
"""
import argparse, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "style-ladder"))
import gen as sl  # noqa: E402

ROOT = Path(__file__).resolve().parent
W, H = 608, 1056
PROMPTS = {
    "portrait": ("Natural-light portrait, close-up of a young woman with short black bob hair and a red jacket, smiling softly, "
                 "looking at the camera, blurred cobblestone street behind her, warm late afternoon sunlight."),
    "walk": ("Cinematic film still, a young woman with short black bob hair and a red jacket walking along a cobblestone street "
             "with trees and parked bicycles, full body, wide shot, warm late afternoon sunlight."),
    "anime": ("Anime illustration, webtoon style, clean thin lineart, cel shading, vibrant colors. A young woman with short black bob hair "
              "and a red jacket stands on a cobblestone street with trees and parked bicycles, full body, wide shot, warm sunlight."),
}


def resize(g):
    for n in g.values():
        i = n["inputs"]
        if "width" in i and "height" in i:
            i["width"], i["height"] = W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+", choices=["wan", "zimage", "klein"])
    ap.add_argument("--seeds", default="101")
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    for model in a.models:
        out = ROOT / "kf" / model
        out.mkdir(parents=True, exist_ok=True)
        for name, prompt in PROMPTS.items():
            prefix = f"vb_kf/{model}_{name}"
            g, tail = sl.MODELS[model](prompt, prefix)
            for s in seeds:
                g.update(tail(s))
            sl.group_decode(g, seeds, prefix)
            resize(g)
            peak = sl.Peak()
            files, dt = sl.run(g)
            mem = peak.stop()
            for s, f in zip(seeds, sorted(files)):
                shutil.copy(f, out / f"{name}_s{s}.png")
            sl.log_line = None
            line = f"{time.strftime('%H:%M:%S')} {model} {name} seeds={seeds} {dt:.0f}s ({dt / len(seeds):.0f}s/img) {mem}"
            print(line, flush=True)
            with open(ROOT / "kf.log", "a") as f:
                f.write(line + "\n")


if __name__ == "__main__":
    main()
