"""Block C1: RIFE x2 vs x5 on a clip mp4 (one graph), then cadence of the 30 fps resamplings.

Usage: python3 rife.py zimage_walk   -> rife/<clip>_x2_*.png, rife/<clip>_x5_*.png ; prints jitter metrics.
Run with the comfy env python (numpy + PIL).
"""
import sys, shutil, time
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "style-ladder"))
import gen as sl  # noqa: E402

ROOT = Path(__file__).resolve().parent
clip = sys.argv[1]
g = {"load": {"class_type": "VHS_LoadVideoPath", "inputs": {"video": str(ROOT / "clips" / f"{clip}.mp4"), "force_rate": 0, "custom_width": 0, "custom_height": 0,
                                                            "frame_load_cap": 0, "skip_first_frames": 0, "select_every_nth": 1}}}
for m in (2, 5):
    g[f"rife{m}"] = {"class_type": "RIFE VFI", "inputs": {"ckpt_name": "rife47.pth", "frames": ["load", 0], "clear_cache_after_n_frames": 10, "multiplier": m,
                                                          "fast_mode": True, "ensemble": True, "scale_factor": 1.0, "dtype": "float16", "torch_compile": False, "batch_size": 1}}
    g[f"save{m}"] = {"class_type": "SaveImage", "inputs": {"images": [f"rife{m}", 0], "filename_prefix": f"vb_rife/{clip}_x{m}"}}
files, dt = sl.run(g)
print(f"rife x2+x5 {dt:.0f}s, {len(files)} files")
for m in (2, 5):
    d = ROOT / "rife" / f"{clip}_x{m}"
    d.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.name.startswith(f"{clip}_x{m}_"):
            shutil.copy(f, d / f.name)


def load(paths, size=(240, 416)):
    return [np.asarray(Image.open(p).convert("L").resize(size), dtype=np.float32) for p in paths]


src = load(sorted((ROOT / "clips" / clip).glob("*.png")))
x2 = load(sorted((ROOT / "rife" / f"{clip}_x2").glob("*.png")))
x5 = load(sorted((ROOT / "rife" / f"{clip}_x5").glob("*.png")))
print("frames src/x2/x5:", len(src), len(x2), len(x5))
n = 60  # 2 s at 30 fps
variants = {
    "24fps nearest (no RIFE)": [src[min(round(i * 24 / 30), len(src) - 1)] for i in range(n)],
    "RIFE x2, pick nearest (current)": [x2[min(round(i * len(x2) / 2.04 / 30 * 1), len(x2) - 1)] for i in range(n)],
    "RIFE x5, every 4th (exact)": [x5[min(i * 4, len(x5) - 1)] for i in range(n)],
}
# Timeline length of the clip: len(src)/24 s; x2 frame k is at k/48 s, x5 frame k at k/120 s (last RIFE frame handling differs, so use measured counts).
variants["RIFE x2, pick nearest (current)"] = [x2[min(round(i * 48 / 30), len(x2) - 1)] for i in range(n)]
for name, fr in variants.items():
    d = np.array([np.abs(fr[i + 1] - fr[i]).mean() for i in range(len(fr) - 1)])
    print(f"{name:34s} mean diff {d.mean():.3f}  jitter(std/mean) {d.std() / d.mean():.3f}  max/mean {d.max() / d.mean():.2f}")
