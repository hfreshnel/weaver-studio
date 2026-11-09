"""Z-Image Turbo 16:9 keyframes for the lighthouse short.

  python3 kf.py <shot> [seeds...]   -> comfyui/output/lh_<shot>_s<seed>_*.png  (1280x720)
Needs ComfyUI on :8188 (--lowvram --disable-pinned-memory).
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "webtoon-layers")); sys.path.insert(0, str(HERE.parent / "style-ladder"))
from bench_cache import run  # noqa: E402
import gen as G  # noqa: E402

STY = ("Still frame from a high-end 3D animated feature film, cinematic CGI render, realistic human proportions, "
       "slightly stylized, detailed skin with subsurface scattering, physically based materials, volumetric light, "
       "soft global illumination, anamorphic cinematic lighting, film grain free.")
CH = ("an elderly lighthouse keeper in his sixties, weathered face with deep wrinkles, short neat white beard, bushy white eyebrows, "
      "pale blue eyes, a dark navy knit wool cap, a thick cream cable-knit fisherman sweater under an open yellow oilskin raincoat")
P = {
    "s1": f"{STY} Wide establishing shot at dusk during a violent storm at sea: a tall white lighthouse with a red band stands on a black rocky cliff "
          "above a raging dark sea, huge waves crash against the rocks with white spray, heavy dark storm clouds, slanting rain, the lighthouse lamp is "
          "dark and unlit, a single small warm window glows at its base. Cold deep blue palette, no people.",
    "s2": f"{STY} Medium close shot, chest-up, of {CH}, seen from outside through a large rain-streaked glass window of the lighthouse lamp room at night. "
          "Raindrops and water streaks on the glass in the foreground. He leans slightly toward the glass and squints, looking past the camera into the "
          "distance with worry. Cold blue light on his face from the stormy night, a faint warm glow inside the room behind him, brass window frame. "
          "His hands are not visible.",
    "s3": f"{STY} Extreme close-up of the face of {CH}, three-quarter view, inside the dark lighthouse lamp room at night. His face is lit by an intense "
          "warm golden light coming from the left side of the frame, from the giant glass lens of the lighthouse, his determined eyes catch the light, "
          "glints on his damp white beard. Deep blue shadows on the other side of his face. His hands are not visible.",
    "s4": f"{STY} Wide shot over a stormy sea at night: a powerful white beam of light from a distant lighthouse on a cliff cuts through the rain and falls "
          "on a small red and white fishing boat tossing on big dark waves in the foreground, its deck wet and shining in the beam, sea spray, heavy rain, "
          "dark storm clouds. Cold blue palette with the bright beam.",
}

if __name__ == "__main__":
    shot, seeds = sys.argv[1], [int(s) for s in sys.argv[2:]] or [11, 12, 13, 14]
    g, tail = G.zimage(P[shot], f"lh_{shot}")
    g["lat"]["inputs"].update(width=1280, height=720)
    graph = dict(g)
    for s in seeds:
        graph.update(tail(s))
    r = run(graph)
    print(shot, json.dumps({k: r[k] for k in ("status", "seconds", "files")}), r.get("error"))
