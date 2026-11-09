"""Z-Image Turbo keyframes on green (comparison with Animagine). python3 zk.py <shot> [seeds...]  -> comfyui/output/zk_<shot>_s<seed>"""
import json, sys
sys.path.insert(0, "../webtoon-layers"); sys.path.insert(0, "../style-ladder")
from bench_cache import run
import gen as G
CH = ("a young schoolgirl with short black bob hair with bangs, amber eyes, a red ribbon in her hair on the side, a small mole under "
      "her left eye, white sailor uniform with navy blue collar and short sleeves, white pleated skirt, white socks and black loafers")
BG = "on a solid flat green background (chroma key green), no shadows, no scenery"
STY = "Anime illustration, webtoon style, clean thin lineart, flat colors, cel shading."
CHF = ("a young schoolgirl with short black bob hair with bangs, amber eyes, a red ribbon in her hair on the side, a small mole under "
       "her left eye, white sailor uniform with navy blue collar")
P = {
     "close2": f"{STY} Close-up portrait of {CHF}: head and shoulders only, front view at eye level, looking straight at the viewer with a gentle smile, the picture is cropped at the chest so no hands and no skirt are visible, {BG}.",
     "back2": f"{STY} Full-body shot of {CH}, seen directly from behind (rear view), walking away from the camera with her back to the viewer, her face is not visible, arms relaxed at her sides, {BG}.",
     "mid2": f"{STY} Waist-up shot of {CHF}, looking up at the sky with a gentle smile, face turned upwards, the picture is cropped at the waist so no hands are visible, {BG}.","front": f"{STY} Full-body shot of {CH}, walking towards the camera, arms relaxed at her sides, hands relaxed, {BG}.",
     "back": f"{STY} Full-body shot of {CH}, seen from behind, walking away from the camera, facing away, back view, arms relaxed at her sides, {BG}.",
     "mid": f"{STY} Waist-up shot of {CH}, looking up at the sky with a gentle smile, face turned upwards, arms relaxed at her sides, {BG}.",
     "close": f"{STY} Close-up portrait of {CH}, looking at the viewer with a gentle smile, shoulders visible, {BG}."}
shot, seeds = sys.argv[1], [int(s) for s in sys.argv[2:]] or [71, 72, 73, 74]
g, tail = G.zimage(P[shot], f"zk_{shot}")
graph = dict(g)
for s in seeds: graph.update(tail(s))
r = run(graph); print(json.dumps({k: r[k] for k in ("status", "seconds", "files")}), r.get("error"))
