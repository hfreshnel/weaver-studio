"""Compositing + edit of the 10 s short (numpy/PIL + ffmpeg).

  python post.py <edit.json> <out.mp4>

edit.json: list of shots, each {"name", "dir", "start", "count", "step"?, "reverse_tail"?, "grade": {...}, "rain": float, "lightup": [f0, f1]}
- dir: folder of 1920x1080 PNG frames, sorted by name; frames start..start+count (step 1 by default).
- grade: exposure (stops), gains [r,g,b], sat, lift (black lift), contrast. Applied in linear-ish float.
- rain: 0..1 opacity of the procedural rain layer (exterior shots).
- lightup: [f0, f1] frame range (shot-local) over which the shot goes from dark/cold moonlight to its keyframe lighting,
  with a short flicker at ignition (S3: the lamp turns on).
Common to all shots: same final curve + vignette, so Blender and AI shots share one look.
"""
import json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = 1.0 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
VIG = np.clip(VIG, 0.55, 1.0)[..., None]


def grade(a, g):
    a = a * (2.0 ** g.get("exposure", 0.0)) * np.array(g.get("gains", [1, 1, 1]), np.float32)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    a = lum[..., None] + (a - lum[..., None]) * g.get("sat", 1.0)
    c = g.get("contrast", 1.0)
    a = 0.5 + (a - 0.5) * c
    lift = g.get("lift", 0.0)
    a = a + lift * (1 - a)
    return a


class Rain:
    """Pre-drawn streak sprites moved each frame; three depth layers (far = thin/slow/dim)."""
    def __init__(self, seed, n=900):
        r = np.random.default_rng(seed)
        self.d = r.uniform(0, 1, n) ** 1.5                           # depth: 0 far .. 1 near
        self.x = r.uniform(-200, W + 200, n); self.y = r.uniform(-H, H, n)
        self.speed = 28 + 70 * self.d                                 # px/frame
        self.len = 18 + 70 * self.d
        self.alpha = 0.18 + 0.5 * self.d
        self.ang = math.radians(12)

    def layer(self, t):
        im = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(im)
        dx, dy = math.sin(self.ang), math.cos(self.ang)
        for x, y, s, ln, al, d in zip(self.x, self.y, self.speed, self.len, self.alpha, self.d):
            yy_ = (y + s * t) % (2 * H) - H * 0.5
            xx_ = x + dx / dy * (yy_ - y)
            dr.line([(xx_, yy_), (xx_ + dx * ln, yy_ + dy * ln)], fill=int(255 * al), width=1 if d < 0.7 else 2)
        return np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., None] / 255.0


WARM = np.clip((xx / W - 0.25) / 0.75, 0, 1)[..., None] ** 1.5 * np.array([1.0, 0.62, 0.28], np.float32)


def lightup(a, f, f0, f1, rng, warmkey=0.0):
    """Dark cold moonlight before f0, ignition flicker, keyframe light + warm key from the lamp side (right) after."""
    a = a * (1 + warmkey * WARM)
    cold = a.mean(axis=2, keepdims=True) * np.array([0.55, 0.7, 1.0], np.float32) * 0.4
    if f < f0: k = 0.0
    elif f >= f1: k = 1.0
    else:
        u = (f - f0) / (f1 - f0)
        k = u * u * (3 - 2 * u)
        if u < 0.45: k *= 0.55 + 0.45 * rng.uniform()               # arc-lamp flicker while it strikes
    return cold * (1 - k) + a * k


def boatlight(a, k, cfg, track):
    """Distant mast light of the boat at the horizon, seen through the window (S2): soft glow, bobbing on the swell,
    following the camera drift measured by phase correlation on the window region."""
    dx, dy = track
    t = k / 24.0
    x = cfg["x"] + dx; y = cfg["y"] + dy + 2.5 * math.sin(2 * math.pi * t / 1.6)
    fade = min(1.0, max(0.0, (k - cfg.get("from", 0)) / 10.0))
    r2 = (xx - x) ** 2 + (yy - y) ** 2
    glow = np.exp(-r2 / (2 * 1.8 ** 2)) * 1.0 + np.exp(-r2 / (2 * 12.0 ** 2)) * 0.22
    r2r = (xx - x + 6) ** 2 + (yy - y - 4) ** 2                           # red sidelight, left and below the mast light
    red = np.exp(-r2r / (2 * 1.5 ** 2)) * 0.8 + np.exp(-r2r / (2 * 7.0 ** 2)) * 0.12
    return a + fade * cfg.get("gain", 1.0) * (glow[..., None] * np.array([1.0, 0.86, 0.62], np.float32)
                                              + red[..., None] * np.array([1.0, 0.12, 0.08], np.float32))


def main():
    edit, out = json.loads(Path(sys.argv[1]).read_text()), sys.argv[2]
    fd = Path(out).with_suffix(""); fd.mkdir(parents=True, exist_ok=True)
    for f in fd.glob("*.png"): f.unlink()
    n = 0
    for si, s in enumerate(edit):
        fs = sorted(Path(s["dir"]).glob("*.png"))
        idx = list(range(s["start"], s["start"] + s["count"] * s.get("step", 1), s.get("step", 1)))
        if s.get("pingpong"):
            idx = idx + idx[-2:0:-1]
        idx = idx[:s.get("max", len(idx))]
        rain = Rain(100 + si) if s.get("rain") else None
        rng = np.random.default_rng(7)
        ref = None
        for k, i in enumerate(idx):
            im = Image.open(fs[min(i, len(fs) - 1)]).convert("RGB")
            if s.get("crop"):                                    # [x0, y0, x1, y1] as fractions of the source
                c = s["crop"]; im = im.crop((round(c[0] * im.width), round(c[1] * im.height), round(c[2] * im.width), round(c[3] * im.height)))
            a = np.asarray(im.resize((W, H), Image.LANCZOS), np.float32) / 255.0
            if s.get("boatlight"):
                import cv2
                x0, y0, x1, y1 = s["boatlight"]["track"]
                g = np.ascontiguousarray(a[y0:y1, x0:x1].mean(axis=2))
                if ref is None: ref = g
                (tdx, tdy), _ = cv2.phaseCorrelate(ref, g)
                a = boatlight(a, k, s["boatlight"], (tdx, tdy))
            a = grade(a, s.get("grade", {}))
            if s.get("lightup"): a = lightup(a, k, *s["lightup"], rng, s.get("warmkey", 0.0))
            if rain is not None:
                a = a + rain.layer(k) * s["rain"] * np.array([0.75, 0.82, 0.9], np.float32)
            a = a * VIG
            a = 1 - np.exp(-np.maximum(a, 0) * 1.6) * 1.0 if s.get("tonemap") else a
            Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(fd / f"{n:04d}.png")
            n += 1
        print(s["name"], len(idx), "frames", flush=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(fd / "%04d.png")]
    if len(sys.argv) > 3: cmd += ["-i", sys.argv[3], "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "15", "-preset", "slow", "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True)
    print("WROTE", out, n, "frames", round(n / 24, 2), "s")


if __name__ == "__main__":
    main()
