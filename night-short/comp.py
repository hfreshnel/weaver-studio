"""Per-frame composite of a matted character on the street decor (shared by shot.py and cycle.py)."""
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, "../webtoon-layers")
import compose as C

import os
F = float(os.environ.get("NS_F", "1"))
SIZE = (round(832 * F), round(1216 * F))
if F == 1:
    DECOR = Image.open("../webtoon-layers/decor_street_00002_.png").convert("RGBA")
else:                                   # sharper base: the x2 anime upscale of the decor, resampled to the output size
    DECOR = Image.open("../comfyui/output/ns_decor_x2_00001_.png").convert("RGBA").resize(SIZE, Image.LANCZOS)


def smooth(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t)


def render(char, s, ox, oy, yb, fx):
    """char: RGBA sprite; (s, ox, oy): sprite -> decor transform; yb: ground row of her feet in the decor; fx: feet x."""
    s, ox, oy, yb, fx = s * F, round(ox * F), round(oy * F), round(yb * F), round(fx * F)   # decor-native units -> output pixels
    ch = char.resize((max(1, round(char.width * s)), max(1, round(char.height * s))), Image.LANCZOS)
    layer = Image.new("RGBA", DECOR.size, (0, 0, 0, 0)); layer.paste(ch, (ox, oy))
    rgba = np.asarray(layer, np.float32); al = rgba[..., 3] / 255
    height = int(C.K * (yb - C.HORIZON * F))
    w_sun = float(smooth(-yb / F, -985, -905))                 # 0 in the shade (y > 985), 1 in the sun band (y < 905)
    bg = np.asarray(DECOR.convert("RGB"), np.float32)
    mul = np.ones_like(bg)
    if w_sun > 0:
        mul *= 1 - (C.cast_shadow(al, yb, 0.85 * w_sun)[..., None]) * (1 - C.SHADE / C.SUN)
    mul *= 1 - C.contact_shadow(al, fx, yb, max(height, 20), 0.85)[..., None] * 0.75
    bg *= mul
    fg_shade = C.grade(rgba[..., :3], "shade", 0.25); fg_sun = C.grade(rgba[..., :3], "sun", 1.0)
    fg = fg_shade * (1 - w_sun) + fg_sun * w_sun
    return Image.fromarray((fg * al[..., None] + bg * (1 - al[..., None])).astype(np.uint8))
