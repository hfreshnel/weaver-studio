"""Z-Image Turbo img2img (relight / restyle while keeping identity).

  python3 i2i.py <name> <image in comfyui/input> "<prompt>" <denoise> [seeds...]  -> comfyui/output/lhi_<name>_d<denoise>_s<seed>
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "webtoon-layers")); sys.path.insert(0, str(HERE.parent / "style-ladder"))
from bench_cache import run  # noqa: E402
import gen as G  # noqa: E402
from kf import STY  # noqa: E402  (kf.py only runs its job under __main__)

name, img, prompt, den = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
seeds = [int(s) for s in sys.argv[5:]] or [21, 22]
g, tail = G.zimage(f"{STY} {prompt}", f"lhi_{name}_d{int(den * 100)}")
g["img"] = {"class_type": "LoadImage", "inputs": {"image": img}}
g["lat"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["img", 0], "vae": ["vae", 0]}}
graph = dict(g)
for s in seeds:
    t = tail(s)
    t[f"ks{s}"]["inputs"]["denoise"] = den
    graph.update(t)
r = run(graph)
print(name, den, json.dumps({k: r[k] for k in ("status", "seconds", "files")}), r.get("error"), flush=True)
