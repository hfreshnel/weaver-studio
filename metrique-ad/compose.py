"""Deterministic 1080x1920@30 compositor for the MÉTRIQUE launch ad.

Renders every frame with Pillow and pipes raw RGB to ffmpeg (H.264).
Missing inputs degrade to placeholders so the layout can be checked early.

Usage:
  .venv/bin/python compose.py                  # full render -> out/metrique_launch_v1.mp4
  .venv/bin/python compose.py --stills 0.5 13 30 --safe   # PNG previews (with safe-zone overlay)
"""
import argparse, json, math, subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
PUB = Path("/home/freshnel/dev/git/Metrics-Services/frontend/public")
FONTS = ROOT / "assets/fonts/inter/extras/ttf"
W, H, FPS, DUR = 1080, 1920, 30, 60.0

NAVY = (13, 27, 42)
GOLD = (251, 192, 45)
WHITE = (255, 255, 255)
MUTED = (87, 98, 115)
SAFE = dict(top=220, bottom=1500, left=90, right=940)


# ---------- helpers ----------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def prog(t, start, dur):
    return ease((t - start) / dur)


@lru_cache(maxsize=None)
def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Inter-{weight}.ttf"), size)


@lru_cache(maxsize=64)
def load(path):
    return Image.open(path).convert("RGBA")


def cover(img, w, h, zoom=1.0, cx=0.5, cy=0.5):
    """Scale-to-cover crop, with optional zoom and focal point."""
    s = max(w / img.width, h / img.height) * zoom
    rw, rh = int(img.width * s), int(img.height * s)
    im = img.resize((rw, rh), Image.LANCZOS)
    x = int(clamp(cx * rw - w / 2, 0, rw - w))
    y = int(clamp(cy * rh - h / 2, 0, rh - h))
    return im.crop((x, y, x + w, y + h))


def grade(img, mode):
    """Per-sequence grade: 'cold' for the problem, 'warm' for the payoff."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    lum = a.mean(axis=2, keepdims=True)
    if mode == "cold":
        a = lum + (a - lum) * 0.6
        a = a * 0.9 + np.array([-6, 0, 10])
    elif mode == "warm":
        a = lum + (a - lum) * 1.08
        a = a + np.array([10, 3, -10])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def text_lines(text, fnt, max_w):
    """Greedy wrap; explicit newlines force a break."""
    lines = []
    for para in text.split("\n"):
        cur = []
        for w_ in para.split():
            if cur and fnt.getlength(" ".join(cur + [w_])) > max_w:
                lines.append(cur)
                cur = [w_]
            else:
                cur.append(w_)
        lines.append(cur)
    return lines


def draw_rich(draw, text, x, y, fnt, color, gold=(), max_w=850, align="left", line_h=1.18, alpha=255):
    """Word-wrapped text; words in `gold` are drawn in the accent color. Returns block height."""
    lines = text_lines(text, fnt, max_w)
    lh = int(fnt.size * line_h)
    for i, words in enumerate(lines):
        line_w = fnt.getlength(" ".join(words))
        cx = x - line_w / 2 if align == "center" else x
        for w_ in words:
            c = GOLD if w_.strip(".,…!?") in gold else color
            draw.text((cx, y + i * lh), w_, font=fnt, fill=c + (alpha,))
            cx += fnt.getlength(w_ + " ")
    return lh * len(lines)


def caption(frame, t, start, text, gold=(), y=1250, size=64):
    """Navy plate caption on AI shots, slides up and fades in."""
    p = prog(t, start, 0.3)
    if p <= 0:
        return
    fnt = font("Bold", size)
    lines = text_lines(text, fnt, 780)
    lh = int(size * 1.18)
    tw = max(fnt.getlength(" ".join(l)) for l in lines)
    pad = 34
    box_w, box_h = tw + pad * 2, lh * len(lines) + pad * 2 - 10
    ox = (W - box_w) / 2
    oy = y + (1 - p) * 40
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((ox, oy, ox + box_w, oy + box_h), 24, fill=NAVY + (int(225 * p),))
    draw_rich(d, text, W / 2, oy + pad - 6, fnt, WHITE, gold, max_w=780, align="center", alpha=int(255 * p))
    frame.alpha_composite(layer)


# ---------- sources ----------

def selected():
    f = ROOT / "selected.json"
    return json.loads(f.read_text()) if f.exists() else {}


def clip_frame(name, t, dur):
    """Frame of a processed AI clip (clips_final/<name>/*.png, 1080x1920), else keyframe still, else placeholder."""
    d = ROOT / "clips_final" / name
    frames = sorted(d.glob("*.png")) if d.exists() else []
    if frames:
        i = min(int(t / dur * len(frames)), len(frames) - 1)
        return Image.open(frames[i]).convert("RGBA").resize((W, H), Image.LANCZOS)
    key = selected().get(name, {}).get("key")
    if key and (ROOT / key).exists():
        return cover(load(ROOT / key), W, H, zoom=1.0 + 0.05 * t / dur)
    im = Image.new("RGBA", (W, H), (40, 48, 60, 255))
    ImageDraw.Draw(im).text((W / 2, H / 2), name, font=font("Bold", 90), fill=WHITE, anchor="mm")
    return im


def screen(name):
    p = ROOT / "assets/screens" / f"{name}.png"
    if p.exists():
        return load(p)
    im = Image.new("RGBA", (1170, 2532), (245, 246, 247, 255))
    ImageDraw.Draw(im).text((585, 1266), name, font=font("Bold", 70), fill=NAVY, anchor="mm")
    return im


@lru_cache(maxsize=4)
def hero_screen(name="home_hero"):
    """Live home hero with the live stats line blurred out (not a claim we want in the ad)."""
    im = screen(name).copy()
    band = (0, 1770, 1170, 1910)
    im.paste(im.crop(band).filter(ImageFilter.GaussianBlur(28)), band[:2])
    return im


# ---------- phone mockup ----------

PH_W = 640
PH_X = (W - PH_W) // 2


def phone(frame, img, t_scroll=0.0, top=560, slide=1.0, taps=(), highlight=None):
    """Phone with a real screenshot; `t_scroll` in screenshot pixels; taps = [(x, y, p)] in screen px."""
    sw = PH_W
    sh = int(sw * 2532 / 1170)
    s = sw / img.width
    y0 = int(t_scroll)
    view = img.crop((0, y0, img.width, min(img.height, y0 + int(sh / s))))
    view = view.resize((sw, int(view.height * s)), Image.LANCZOS)
    scr = Image.new("RGBA", (sw, sh), WHITE + (255,))
    scr.paste(view, (0, 0))
    d = ImageDraw.Draw(scr)
    if highlight:
        hx0, hy0, hx1, hy1, hp = highlight
        if hp > 0:
            r = [v * s for v in (hx0, hy0 - y0, hx1, hy1 - y0)]
            d.rounded_rectangle((r[0] - 8, r[1] - 8, r[2] + 8, r[3] + 8), 18, outline=GOLD + (int(255 * hp),), width=7)
    for (tx, ty, tp) in taps:
        if 0 < tp < 1:
            rad = 20 + 50 * tp
            cx, cy = tx * s, (ty - y0) * s
            d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=GOLD + (int(150 * (1 - tp)),))
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw, sh), 44, fill=255)
    yy = int(top + (1 - slide) * (H - top))
    body = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle((PH_X - 14, yy - 14, PH_X + sw + 14, yy + sh + 14), 58, fill=NAVY + (255,))
    frame.alpha_composite(body)
    frame.paste(scr, (PH_X, yy), mask)


def step_header(frame, t, start, num, title, sub):
    d = ImageDraw.Draw(frame)
    p = prog(t, start, 0.35)
    a = int(255 * p)
    x = SAFE["left"] + 10
    y = 250 + (1 - p) * 30
    d.ellipse((x, y, x + 96, y + 96), fill=GOLD + (a,))
    d.text((x + 48, y + 50), str(num), font=font("Bold", 58), fill=NAVY + (a,), anchor="mm")
    d.text((x + 124, y + 2), title, font=font("Bold", 72), fill=NAVY + (a,))
    draw_rich(d, sub, x, y + 118, font("Medium", 40), MUTED, max_w=840, alpha=a)


def demo_note(frame):
    ImageDraw.Draw(frame).text((W / 2, 545), "Interface réelle — données de démonstration",
                               font=font("Medium", 26), fill=MUTED + (255,), anchor="mm")


# ---------- segments ----------

def seg_ai(name, start, dur, mode, cap, gold=()):
    def draw(t):
        f = grade(clip_frame(name, t - start, dur), mode) if mode else clip_frame(name, t - start, dur)
        if cap:
            caption(f, t, start + 0.1, cap, gold)
        return f
    return (start, start + dur, draw)


def mg1(t):  # 12-15 navy reveal + logo
    f = Image.new("RGBA", (W, H), NAVY + (255,))
    d = ImageDraw.Draw(f)
    p = prog(t, 12.15, 0.5)
    d.rectangle((W / 2 - 300 * p, 1060, W / 2 + 300 * p, 1066), fill=GOLD)
    lp = prog(t, 12.4, 0.6)
    logo = load(PUB / "logo-metrique-nav-dark.png")
    lw = int(760 * (0.92 + 0.08 * lp))
    lg = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
    lg.putalpha(lg.getchannel("A").point(lambda v: int(v * lp)))
    f.alpha_composite(lg, (int((W - lw) / 2), int(1020 - lg.height)))
    sp = prog(t, 13.1, 0.4)
    d.text((W / 2, 1130 + (1 - sp) * 20), "Services au Bénin", font=font("Medium", 52),
           fill=(241, 245, 249, int(255 * sp)), anchor="mt")
    return f


def mg2(t):  # 15-19 H1 typography then phone with the live hero
    f = Image.new("RGBA", (W, H), WHITE + (255,))
    d = ImageDraw.Draw(f)
    words = "Trouvez le bon\n professionnel\n près de vous.".split(" ")
    n = int(clamp((t - 15.0) / 0.9) * len(words) + 0.999)
    rise = prog(t, 16.4, 0.6)
    size = int(92 - 28 * rise)
    y = 760 - 480 * rise
    draw_rich(d, " ".join(words[:n]), W / 2, y, font("Bold", size), NAVY, gold=("professionnel",), max_w=860, align="center")
    if t > 16.4:
        phone(f, hero_screen(), top=600, slide=prog(t, 16.4, 0.7))
    return f


ILLUS = ["plumbing", "electricity", "hairdressing", "it", "design"]
CHIPS = ["Plomberie", "Électricité", "Coiffure", "Informatique", "Design graphique"]


def mg3(t):  # 19-22 sectors: real illustrations + real chip labels
    lt = t - 19.0
    i = min(int(lt / 0.6), 4)
    img = load(PUB / f"home/services/service-{ILLUS[i]}.png")
    f = cover(img, W, H, zoom=1.0 + 0.06 * ((lt - i * 0.6) / 0.6), cx=0.3 if i == 0 else 0.5)
    shade = Image.new("RGBA", (W, H), NAVY + (70,))
    f.alpha_composite(shade)
    d = ImageDraw.Draw(f)
    fnt = font("SemiBold", 40)
    x, y = SAFE["left"], 1080
    for k, chip in enumerate(CHIPS):
        p = prog(t, 19.0 + k * 0.45, 0.25)
        if p <= 0:
            continue
        cw = fnt.getlength(chip) + 56
        if x + cw > SAFE["right"] + 40:
            x, y = SAFE["left"], y + 96
        active = k == i
        d.rounded_rectangle((x, y + (1 - p) * 20, x + cw, y + 76 + (1 - p) * 20), 38,
                            fill=(GOLD if active else WHITE) + (int(245 * p),))
        d.text((x + 28, y + 16 + (1 - p) * 20), chip, font=fnt, fill=NAVY + (int(255 * p),))
        x += cw + 18
    caption(f, t, 19.2, "Plombiers, électriciens,\ncoiffeurs, développeurs…\nau Bénin.", y=1300, size=50)
    return f


def mg4(t):  # 22-28 step 1: search
    if 25.5 <= t < 27.0:
        return grade(clip_frame("P06", t - 25.5, 1.5), "warm")
    f = Image.new("RGBA", (W, H), WHITE + (255,))
    step_header(f, t, 22.0, 1, "Cherchez", "Un métier, un service, une ville.")
    card = selected().get("highlights", {}).get("card")
    if t < 23.2:
        phone(f, hero_screen(), top=600, slide=prog(t, 22.0, 0.5), taps=[(585, 1135, (t - 22.7) / 0.5)])
    elif t < 24.4:
        phone(f, hero_screen("home_search_filled"), top=600, taps=[(585, 1302, (t - 23.8) / 0.5)])
    else:
        h = (*card, prog(t, 24.8, 0.4)) if card else None
        phone(f, screen("demo_results"), top=600, highlight=h, taps=[(300, 1800, (t - 27.2) / 0.5)])
    demo_note(f)
    return f


def mg5(t):  # 28-34 step 2: compare (verified provider -> packs -> verified identity)
    f = Image.new("RGBA", (W, H), WHITE + (255,))
    step_header(f, t, 28.0, 2, "Comparez", "Prix, avis et identité vérifiée.")
    hl = selected().get("highlights", {})
    # Scroll keyframes (screenshot px): photo -> verified badge -> packs -> verified identity.
    scroll = (1300 * prog(t, 28.3, 0.6)
              + (hl.get("packs_scroll", 3700) - 1300) * prog(t, 30.4, 0.9)
              + 1000 * prog(t, 32.6, 0.5))
    h = None
    if 29.0 <= t < 30.4 and "prest_verifie" in hl:
        h = (*hl["prest_verifie"], prog(t, 29.0, 0.4))
    elif 31.4 <= t < 32.6 and "packs" in hl:
        h = (*hl["packs"], prog(t, 31.4, 0.4))
    elif t >= 33.0 and "identite" in hl:
        h = (*hl["identite"], prog(t, 33.0, 0.3))
    phone(f, screen("demo_service"), top=600, t_scroll=scroll, highlight=h)
    demo_note(f)
    return f


def mg6(t):  # 34-40 step 3: order + escrow
    if 37.0 <= t < 38.5:
        return grade(clip_frame("P07", t - 37.0, 1.5), "warm")
    f = Image.new("RGBA", (W, H), WHITE + (255,))
    step_header(f, t, 34.0, 3, "Commandez", "Échangez avec le prestataire et payez par Mobile Money.")
    hl = selected().get("highlights", {})
    if t < 37.0:
        phone(f, screen("demo_messages"), top=600, t_scroll=0)
    else:  # 38.5-40 payment page, escrow line highlighted
        h = (*hl["escrow"], prog(t, 38.7, 0.3)) if "escrow" in hl else None
        phone(f, screen("demo_payment"), top=600, t_scroll=hl.get("escrow_scroll", 0), highlight=h)
    if t >= 38.6:
        caption(f, t, 38.6, "Vos fonds restent en séquestre\njusqu'à votre confirmation.", gold=("séquestre",), y=1300, size=46)
    demo_note(f)
    return f


def mg7(t):  # 52-60 final card
    f = Image.new("RGBA", (W, H), WHITE + (255,))
    d = ImageDraw.Draw(f)
    if t < 54.6:
        p = prog(t, 52.1, 0.4)
        draw_rich(d, "Arrêtez de parier sur un numéro WhatsApp.", W / 2, 760 + (1 - p) * 30, font("Bold", 84), NAVY,
                  gold=("parier",), max_w=880, align="center", alpha=int(255 * p))
        return f
    p = prog(t, 54.6, 0.5)
    logo = load(PUB / "logo-metrique-nav-light.png")
    lw = 720
    lg = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
    lg.putalpha(lg.getchannel("A").point(lambda v: int(v * p)))
    f.alpha_composite(lg, ((W - lw) // 2, 560))
    bp = prog(t, 55.0, 0.4)
    fnt = font("Bold", 36)
    label = "Trouver un professionnel maintenant"
    bw = fnt.getlength(label) + 80
    bx, by = (W - bw) / 2, 980 + (1 - bp) * 20
    d.rounded_rectangle((bx, by, bx + bw, by + 100), 50, fill=GOLD + (int(255 * bp),))
    d.text((W / 2, by + 50), label, font=fnt, fill=NAVY + (int(255 * bp),), anchor="mm")
    up = prog(t, 55.4, 0.4)
    d.text((W / 2, 1170), "metriqueservices.org", font=font("SemiBold", 56), fill=NAVY + (int(255 * up),), anchor="mt")
    return f


TIMELINE = [
    seg_ai("P01", 0.0, 2.0, "cold", "Trouver un pro\nau Bénin…"),
    seg_ai("P02", 2.0, 1.0, "cold", "…c'est un pari.", gold=("pari",)),
    seg_ai("P03", 3.0, 3.0, "cold", "Un numéro WhatsApp.\nAucun avis fiable."),
    seg_ai("P04", 6.0, 3.0, "cold", "Vous payez d'avance…"),
    seg_ai("P05", 9.0, 3.0, "cold", "…et le prestataire\ndisparaît.", gold=("disparaît",)),
    (12.0, 15.0, mg1),
    (15.0, 19.0, mg2),
    (19.0, 22.0, mg3),
    (22.0, 28.0, mg4),
    (28.0, 34.0, mg5),
    (34.0, 40.0, mg6),
    seg_ai("P08", 40.0, 3.0, "warm", "Le bon pro, vérifié.", gold=("vérifié",)),
    seg_ai("P09", 43.0, 3.0, "warm", "Le travail est fait."),
    seg_ai("P10", 46.0, 3.0, "warm", "Vous confirmez.\nIl est payé.", gold=("payé",)),
    seg_ai("P11", 49.0, 3.0, "warm", "MÉTRIQUE transforme\nle bouche-à-oreille\nen commande sécurisée.", gold=("sécurisée",)),
    (52.0, 60.0, mg7),
]


def transitions(t, f):
    # Navy wipe rising from the bottom into the reveal (11.6 -> 12.0).
    if 11.6 <= t < 12.0:
        p = ease((t - 11.6) / 0.4)
        ImageDraw.Draw(f).rectangle((0, H * (1 - p), W, H), fill=NAVY)
        ImageDraw.Draw(f).rectangle((0, H * (1 - p) - 8, W, H * (1 - p)), fill=GOLD)
    # Gold wipe between demo steps.
    for tt in (27.75, 33.75):
        if tt <= t < tt + 0.5:
            p = (t - tt) / 0.5
            x = W * (2 * p - 0.5)
            ImageDraw.Draw(f).rectangle((x - W / 2, 0, x + W / 2, H), fill=GOLD)
    # Fade to white into the final card.
    if 51.6 <= t < 52.0:
        a = int(255 * (t - 51.6) / 0.4)
        f.alpha_composite(Image.new("RGBA", (W, H), WHITE + (a,)))
    return f


def render(t, safe=False):
    for start, end, draw in TIMELINE:
        if start <= t < end:
            f = transitions(t, draw(t))
            break
    else:
        f = mg7(59.99)
    if safe:
        d = ImageDraw.Draw(f)
        d.rectangle((0, 0, W, SAFE["top"]), outline=(255, 0, 0, 255), width=4)
        d.rectangle((0, SAFE["bottom"], W, H), outline=(255, 0, 0, 255), width=4)
        d.rectangle((SAFE["right"] + 0, 0, W, H), outline=(255, 0, 0, 255), width=4)
    return f.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", type=float, nargs="*")
    ap.add_argument("--safe", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "out/metrique_launch_v1.mp4"))
    a = ap.parse_args()
    if a.stills is not None:
        for s in a.stills:
            p = ROOT / "out" / f"still_{s:05.2f}.png"
            render(s, a.safe).save(p)
            print(p)
        return
    n = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(render(i / FPS, a.safe).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(a.out)


if __name__ == "__main__":
    main()
