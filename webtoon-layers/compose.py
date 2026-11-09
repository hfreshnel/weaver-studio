"""Composite the matted character over a fixed decor, with ground shadows, light grading and an optional camera move.

  python -I compose.py --preset contact --sheet 0,24,48          # stills only -> eval/sheet_<preset>.png
  python -I compose.py --preset sun_cast --video                  # all frames -> eval/<preset>.mp4

Presets are defined in PRESETS below.
"""
import argparse, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "eval"

# Road colours sampled in decor_street_00002_: building shade at the bottom of the frame vs the sunlit patch.
SHADE = np.array([117, 121, 139], np.float32)
SUN = np.array([239, 211, 196], np.float32)
# Horizon of decor_street_00002_ (Hough vanishing point at x=381, y=685). The character frame height is
# K * (feet_y - HORIZON): K = 1.9 keeps the previous framing (frame = 80 % of the decor, feet at y=1196).
HORIZON, K = 685, 1.904

PRESETS = {
    # Previous composite: feet 20 px above the bottom, centred, no shadow, no grade.
    "base": dict(feet_x=416, feet_y=1196),
    "contact": dict(feet_x=416, feet_y=1196, contact=0.85),
    # Standing in the building shade: darken and cool the character by part of the shade/sun ratio.
    "shade": dict(feet_x=416, feet_y=1196, contact=0.85, grade="shade", grade_amount=0.35),
    # Further down the street, feet in the sunlit band (y 880-970): warm tint + shadow cast to the right.
    "sun_cast": dict(feet_x=430, feet_y=945, contact=0.85, cast=0.85, grade="sun", grade_amount=1.0),
    # Waist-up tracking shot: feet off-frame (no foot sliding to hide), decor zooms out around the vanishing point
    # as the camera tracks back in front of her (zoom 1.12 -> 1.0, eased).
    "track": dict(feet_x=416, feet_y=1640, grade="shade", grade_amount=0.25, zoom=(1.12, 1.0)),
    "track_static": dict(feet_x=416, feet_y=1640, grade="shade", grade_amount=0.25),
    # Static camera, she really walks towards it (gen.py front). Wan's implied perspective, fitted on the clip:
    # height = 1.187 * (feet_row - 225), R2 0.997. Scale 0.987 and offset map that horizon (y 225) onto the decor
    # horizon (685) and her walking line (x 256) onto the vanishing point (381): one fixed transform, no camera move.
    "front_walk": dict(place=(0.987, 128, 463), matte="layers/front_s11", frames=29, contact=0.85,
                       grade="shade", grade_amount=0.25),
    # Slower take (front_s12): horizon y 212, walking line x 259, scale 1.3; feet stay in the building shade
    # (decor y 1049 -> 1106). The last 2 frames jump (background tint change) and are dropped.
    "front_walk2": dict(place=(1.3, 44, 409), matte="layers/front_s12", frames=47, contact=0.85,
                        grade="shade", grade_amount=0.25),
}
VP_X = 381


def contact_shadow(alpha, cx, ybot, height, strength):
    """Soft dark blob under the feet: the lowest 5 % of the silhouette, squashed flat and blurred."""
    band = np.zeros_like(alpha)
    top = int(ybot - 0.05 * height)
    band[top:ybot + 1] = alpha[top:ybot + 1]
    im = Image.fromarray((band * 255).astype(np.uint8))
    # Widen x1.6 around the feet centre so it shows around the shoes, squash x0.25 around the feet row, then blur.
    sx, sy = 1.6, 0.25
    squashed = im.transform(im.size, Image.AFFINE, (1 / sx, 0, cx - cx / sx, 0, 1 / sy, ybot - ybot / sy), Image.BILINEAR)
    blur = squashed.filter(ImageFilter.GaussianBlur(float(max(2, height * 0.01))))
    return np.asarray(blur, np.float32) / 255 * strength


def cast_shadow(alpha, ybot, strength, dx=0.75, dy=0.16):
    """Project the silhouette onto the ground: each pixel at height t above the feet lands at (x + t*dx, ybot + t*dy)."""
    im = Image.fromarray((alpha * 255).astype(np.uint8))
    k = dx / dy
    proj = im.transform(im.size, Image.AFFINE, (1, -k, k * ybot, 0, -1 / dy, ybot + ybot / dy), Image.BILINEAR)
    proj = np.asarray(proj.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    proj[: ybot - 2] = 0  # the shadow only exists on the ground, below the feet row
    return proj * strength


def grade(rgb, mode, amount):
    if mode == "shade":
        ratio = SHADE / SUN
    elif mode == "sun":
        ratio = SUN / SUN.max()  # warm tint, keep the brightest channel unchanged
        ratio = 1 - (1 - ratio) * 0.35  # sunlight on a white shirt is much less saturated than on the road
    else:
        return rgb
    ratio = 1 - (1 - ratio) * amount
    return np.clip(rgb * ratio, 0, 255)


def clip_anchor(files):
    """Feet row and legs centre of the whole clip, in source pixels (medians, so a lifted foot or a raised arm
    does not move the character: the source camera is static, one transform for every frame)."""
    rows, cxs = [], []
    for f in files:
        a = np.asarray(Image.open(f))[..., 3] > 128
        ys, xs = np.nonzero(a)
        rows.append(ys.max())
        legs = ys > ys.max() - 0.1 * (ys.max() - ys.min())
        cxs.append((xs[legs].min() + xs[legs].max()) / 2)
    return float(np.median(cxs)), float(np.median(rows))


def zoom_decor(decor, z):
    """Scale the decor by z around the vanishing point, keeping the frame size (z >= 1, so no border appears)."""
    DW, DH = decor.size
    x0, y0 = VP_X - VP_X / z, HORIZON - HORIZON / z
    return decor.transform(decor.size, Image.AFFINE, (1 / z, 0, x0, 0, 1 / z, y0), Image.BICUBIC)


def placements(files, o):
    """Per frame: (scale, ox, oy, feet_x, feet_row) in decor pixels."""
    h = Image.open(files[0]).height
    if "place" not in o:
        cx, row = clip_anchor(files)
        ybot = o["feet_y"]
        s = K * (ybot - HORIZON) / h
        return [(s, round(o["feet_x"] - cx * s), round(ybot - row * s), o["feet_x"], ybot)] * len(files)
    # Fixed transform; the ground contact row moves with her: lowest silhouette row per frame, made monotone
    # (she only comes closer) and smoothed over 5 frames so a lifted foot does not make the shadow jump.
    s, ox, oy = o["place"]
    cx, _ = clip_anchor(files)
    rows = np.maximum.accumulate([np.nonzero((np.asarray(Image.open(f))[..., 3] > 128).any(1))[0].max() for f in files])
    rows = np.convolve(np.pad(rows.astype(float), 2, mode="edge"), np.ones(5) / 5, mode="valid")
    return [(s, ox, oy, round(cx * s + ox), round(r * s + oy)) for r in rows]


def compose(decor, char, o, pl, t=0.0):
    """pl: placement from placements(); t in [0, 1]: position of the frame in the clip, drives the camera move."""
    if o.get("zoom"):
        z0, z1 = o["zoom"]
        e = 0.5 - 0.5 * np.cos(np.pi * t)  # ease in/out
        decor = zoom_decor(decor, z0 + (z1 - z0) * e)
    s, ox, oy, feet_x, ybot = pl
    ch = char.resize((round(char.width * s), round(char.height * s)), Image.LANCZOS)
    layer = Image.new("RGBA", decor.size, (0, 0, 0, 0))
    layer.paste(ch, (ox, oy))
    rgba = np.asarray(layer, np.float32)
    alpha = rgba[..., 3] / 255
    height = int(K * (ybot - HORIZON))

    bg = np.asarray(decor.convert("RGB"), np.float32)
    shadow_mul = np.ones_like(bg)
    if o.get("cast"):
        sh = cast_shadow(alpha, ybot, o["cast"])[..., None]
        shadow_mul *= 1 - sh * (1 - SHADE / SUN)  # sunlit road -> shaded road colour
    if o.get("contact"):
        sh = contact_shadow(alpha, feet_x, ybot, height, o["contact"])[..., None]
        shadow_mul *= 1 - sh * 0.75
    bg = bg * shadow_mul

    fg = grade(rgba[..., :3], o.get("grade"), o.get("grade_amount", 0))
    out = fg * alpha[..., None] + bg * (1 - alpha[..., None])
    return Image.fromarray(out.astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="base", choices=PRESETS)
    ap.add_argument("--decor", default=str(ROOT / "decor_street_00002_.png"))
    ap.add_argument("--matte", help="matted frames dir (default: the preset's, else matte_isnet-anime+despill)")
    ap.add_argument("--sheet", help="comma-separated frame indices for a still sheet")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--frames", type=int, help="keep only the first N frames (default: the preset's, else all)")
    args = ap.parse_args()
    o = PRESETS[args.preset]
    decor = Image.open(args.decor).convert("RGBA")
    files = sorted((ROOT / (args.matte or o.get("matte", "matte_isnet-anime+despill"))).glob("*.png"))
    frames = args.frames or o.get("frames")
    if frames:
        files = files[:frames]
    pls = placements(files, o)
    OUT.mkdir(exist_ok=True)
    if args.sheet:
        n = max(len(files) - 1, 1)
        ims = [compose(decor, Image.open(files[int(i)]), o, pls[int(i)], int(i) / n) for i in args.sheet.split(",")]
        sheet = Image.new("RGB", (sum(i.width for i in ims), ims[0].height))
        for k, im in enumerate(ims):
            sheet.paste(im, (k * im.width, 0))
        sheet.save(OUT / f"sheet_{args.preset}.png")
    if args.video:
        d = OUT / f"frames_{args.preset}"
        d.mkdir(exist_ok=True)
        for i, f in enumerate(files):
            compose(decor, Image.open(f), o, pls[i], i / max(len(files) - 1, 1)).save(d / f"{i:04d}.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(d / "%04d.png"),
                        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(OUT / f"{args.preset}.mp4")], check=True)
    print("done", args.preset)


if __name__ == "__main__":
    main()
