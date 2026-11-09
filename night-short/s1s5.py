"""S1 (pull-back from the canopy) and S5 (slow push-in on the empty street), decor x2 + petal layer."""
import os, sys
from PIL import Image
from lib import *

SUF = os.environ.get("NS_SUF", "")
d2 = Image.open(DECOR2).convert("RGB")
pet = Petals()
for name, n, cam in [("s1", 72, lambda t: (1.5 - 0.5 * ease(t), 560 - 144 * ease(t), 330 + 278 * ease(t))),
                     ("s5", 48, lambda t: (1.0 + 0.10 * ease(t), 416 - 35 * ease(t), 608 - 20 * ease(t)))]:
    name = name + SUF; os.makedirs(f"frames/{name}", exist_ok=True)
    for i in range(n):
        z, cx, cy = cam(i / (n - 1))
        over(camera(d2, z, cx, cy), pet.frame(i + (200 if name == "s5" else 0))).save(f"frames/{name}/{i:04d}.png")
    save_video(f"frames/{name}", f"{name}.mp4")
    print(name, n)
