"""Cut the character out of every frame of src/ with one method, write RGBA PNGs to matte_<method>/.

  python -I matte.py chroma|isnet-anime|birefnet-general
"""
import sys, time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent
method = sys.argv[1]
frames = sorted((ROOT / "src").glob("*.png"))
dst = ROOT / f"matte_{method}"
dst.mkdir(exist_ok=True)


def chroma(im):
    # Background colour = median of the frame border; alpha ramps with RGB distance to it,
    # then the background is unmixed from semi-transparent edge pixels (removes green spill).
    a = np.asarray(im, dtype=np.float32)
    border = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3), a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    d = np.linalg.norm(a - bg, axis=2)
    alpha = np.clip((d - 18) / (60 - 18), 0, 1)
    # Drop specks left on the background (e.g. a stray white mark from Wan): keep blobs >= 2% of the largest.
    lab, n = ndimage.label(alpha > 0.05)
    if n > 1:
        area = ndimage.sum(np.ones_like(alpha), lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.flatnonzero(area >= 0.02 * area.max()))
        alpha = alpha * keep
    # Shaded whites close to the pastel key go translucent inside the body: force the interior opaque,
    # but leave pure-key pixels (alpha 0, e.g. background seen between an arm and the torso) transparent.
    inner = ndimage.binary_erosion(ndimage.binary_fill_holes(alpha > 0.5), iterations=3)
    alpha[inner & (alpha > 0)] = 1
    al = alpha[..., None]
    fg = np.where(al > 0.01, (a - (1 - al) * bg) / np.maximum(al, 0.01), 0)
    rgba = np.dstack([np.clip(fg, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


if method == "chroma":
    cut = chroma
else:
    from rembg import new_session, remove
    session = new_session(method)
    cut = lambda im: remove(im, session=session)

t0 = time.time()
for f in frames:
    cut(Image.open(f).convert("RGB")).save(dst / f.name)
dt = time.time() - t0
print(f"{method}: {len(frames)} frames, {dt:.1f}s ({dt / len(frames):.2f} s/frame)")
