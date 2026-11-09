"""Shared pieces for the night short: camera window on the x2 decor and a procedural petal layer."""
import math, random
import numpy as np
from PIL import Image, ImageDraw

import os
F = float(os.environ.get("NS_F", "1"))     # output scale: 1 = 832x1216, 1.5 = 1248x1824
W, H = round(832 * F), round(1216 * F)
DECOR2 = "../comfyui/output/ns_decor_x2_00001_.png"


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


def camera(decor2, zoom, cx, cy, out=(W, H)):
    """Window of the x2 decor: zoom 1.0 = full frame; (cx, cy) = window centre in decor-native pixels (832x1216)."""
    ww, wh = 832 / zoom, 1216 / zoom
    x0 = min(max(cx - ww / 2, 0), 832 - ww); y0 = min(max(cy - wh / 2, 0), 1216 - wh)
    box = (x0 * 2, y0 * 2, (x0 + ww) * 2, (y0 + wh) * 2)
    return decor2.resize(out, Image.LANCZOS, box=box)


class Petals:
    """Flat pink petals falling with a light wind. Depth z in [0.6, 1.6]: bigger and faster when closer (parallax)."""
    def __init__(self, n=34, seed=5, size=(W, H)):
        r = random.Random(seed)
        self.size = size
        self.p = [dict(x=r.uniform(0, size[0]), y=r.uniform(-size[1], size[1]), z=r.uniform(0.6, 1.6), ph=r.uniform(0, 6.28),
                       rot=r.uniform(0, 6.28), spin=r.uniform(-0.08, 0.08), tone=r.choice([(250, 190, 205), (246, 170, 190), (255, 210, 218)]))
                  for _ in range(n)]

    def frame(self, f, fps=24, twos=True):
        """RGBA overlay for frame f; petals move on twos (12 positions/s) like the rest of the animation."""
        f = f - (f % 2) if twos else f
        S = 2
        im = Image.new("RGBA", (self.size[0] * S, self.size[1] * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        w, h = self.size
        for p in self.p:
            fall = 55 * F * p["z"] / fps                       # px per frame
            y = (p["y"] + f * fall) % (h + 60) - 30
            x = (p["x"] + f * 14 * F * p["z"] / fps + 18 * F * p["z"] * math.sin(p["ph"] + f * 0.05)) % w
            a = p["rot"] + p["spin"] * f
            L, T = 9 * F * p["z"], 5 * F * p["z"]
            pts = []
            for k in range(14):                              # petal outline: ellipse pinched at one end
                t = k / 14 * 2 * math.pi
                ex, ey = L * math.cos(t), T * math.sin(t) * (0.75 + 0.25 * math.cos(t))
                pts.append(((x + ex * math.cos(a) - ey * math.sin(a)) * S, (y + ex * math.sin(a) + ey * math.cos(a)) * S))
            d.polygon(pts, fill=p["tone"] + (235,), outline=(200, 120, 150, 255))
        return im.resize(self.size, Image.LANCZOS)


def over(base, overlay):
    b = base.convert("RGBA"); b.alpha_composite(overlay); return b.convert("RGB")


def save_video(frames_dir, out, fps=24):
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{frames_dir}/%04d.png",
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], check=True)
