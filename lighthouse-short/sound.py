"""Procedural sound track for the 10 s short (numpy/scipy, 48 kHz stereo WAV).

  python sound.py <out.wav> [cues.json]

Cues (seconds) follow the time sheet: shot cuts, lamp ignition, beam crossing the boat, wave crashes.
Layers: rain (exterior bright / interior muffled), wind howl, waves, distant thunder, lamp clunk + hum + whoosh,
a soft pad moving from D minor to B-flat major / D major when the lamp turns on.
"""
import json, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR, DUR = 48000, 10.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(3)
C = {"cuts": [2.5, 5.0, 7.0], "interior": [2.5, 7.0], "ignite": 5.5, "boat": 8.6, "waves": [0.9, 2.1, 7.5, 9.1], "thunder": 0.15}
if len(sys.argv) > 2:
    C.update(json.load(open(sys.argv[2])))


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x)


def env(a, d, s=None):
    """Smooth 0..1 ramp from a to d seconds (raised cosine)."""
    u = np.clip((t - a) / max(d - a, 1e-6), 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * u)


def stereo(m, width=0.0, seed=0):
    r = np.random.default_rng(seed)
    if width == 0: return np.stack([m, m], 1)
    d = int(width * SR / 1000)
    return np.stack([m, np.roll(m, d)], 1)


inside = np.zeros(N)
a, b = C["interior"]
inside = env(a - 0.02, a + 0.02) * (1 - env(b - 0.02, b + 0.02))   # hard cuts, 20 ms crossfade

# rain: bright hiss outside, muffled drumming on glass inside
w = rng.standard_normal(N)
rain_out = bp(w, 900, 9000) * 0.20 + bp(rng.standard_normal(N), 200, 900) * 0.08
drops = (rng.random(N) < 0.004) * rng.standard_normal(N)
rain_in = lp(w, 700) * 0.25 + lp(drops, 2500) * 0.9
rain = rain_out * (1 - inside) + rain_in * inside

# wind: brown noise, slow gusts, a resonant howl
brown = np.cumsum(rng.standard_normal(N)); brown = signal.detrend(brown); brown /= np.abs(brown).max()
gust = 0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t + 1.0) * np.sin(2 * np.pi * 0.11 * t)
howl = bp(rng.standard_normal(N), 380, 470, 4) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.31 * t))
wind = (lp(brown, 300) * 0.9 + howl * 2.5) * gust
wind = wind * (1 - 0.6 * inside)

# waves crashing (outside cues only louder)
waves = np.zeros(N)
for c in C["waves"]:
    e = np.exp(-np.maximum(t - c, 0) / 0.7) * (t >= c) * (1 - np.exp(-np.maximum(t - c, 0) / 0.05))
    waves += lp(rng.standard_normal(N), 1200) * e * 0.9 + bp(rng.standard_normal(N), 1500, 6000) * e * 0.25
waves *= (1 - 0.75 * inside)

# distant thunder at the top of S1
th = C["thunder"]; e = np.exp(-np.maximum(t - th, 0) / 1.6) * (1 - np.exp(-np.maximum(t - th, 0) / 0.25)) * (t >= th)
thunder = lp(brown * 3 + rng.standard_normal(N) * 0.3, 140, 4) * e * 2.5

# lamp: relay clunk, then electric hum rising, plus a low whoosh of light
ig = C["ignite"]; dt = np.maximum(t - ig, 0); on = t >= ig
clunk = (np.sin(2 * np.pi * 95 * dt) * np.exp(-dt / 0.08) + lp(rng.standard_normal(N), 3000) * np.exp(-dt / 0.015)) * on * 1.2
hum = sum(np.sin(2 * np.pi * f * t) / (k + 1) for k, f in enumerate((50, 100, 150, 200, 300)))
hum = hum * env(ig, ig + 0.6) * 0.07 * (0.5 + 0.5 * inside)
whoosh = lp(rng.standard_normal(N), 250) * np.exp(-dt / 1.2) * (1 - np.exp(-dt / 0.3)) * on * 2.2

# pad: D minor before ignition, Bb major -> D major after, slow attack, filtered saws
def saw(f):
    ph = (f * t + rng.random()) % 1.0
    return 2 * ph - 1


def chord(freqs):
    return sum(saw(f) + saw(f * 1.004) for f in freqs) / (2 * len(freqs))


minor = chord([73.42, 146.83, 174.61, 220.0])          # D2 D3 F3 A3
bflat = chord([58.27, 116.54, 146.83, 174.61, 233.08])  # Bb1 Bb2 D3 F3 Bb3
major = chord([73.42, 146.83, 185.0, 220.0, 293.66])    # D2 D3 F#3 A3 D4
k1 = env(ig - 0.1, ig + 0.4); k2 = env(C["boat"] - 0.6, C["boat"] + 0.3)
pad = minor * (1 - k1) + bflat * k1 * (1 - k2) + major * k2
pad = lp(pad, 900, 2) * (0.10 + 0.12 * env(0, 2.0) + 0.18 * k1 + 0.12 * k2)
pad *= 1 - env(DUR - 0.9, DUR)                          # fade out at the end
# the boat answers: a distant horn after the beam found it (two partials + slight detune, soft attack, echo off the cliff)
hn = C.get("horn", 9.05); dh = np.maximum(t - hn, 0)
henv = (1 - np.exp(-dh / 0.08)) * np.exp(-np.maximum(dh - 0.55, 0) / 0.25) * (t >= hn)
horn = sum(a_ * np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.7 * t) * 0.2) for f, a_ in ((98, 1.0), (98.6, 0.7), (196, 0.45), (294, 0.2)))
horn = lp(horn * henv, 700) * 0.4
horn = horn + np.roll(horn, int(0.31 * SR)) * 0.3
mix = (stereo(horn, 2.0) + stereo(rain, 0.6) * 0.55 + stereo(wind, 1.5) * 0.5 + stereo(waves, 0.9) * 0.6 + stereo(thunder) * 0.7
       + stereo(clunk) * 0.6 + stereo(hum) + stereo(whoosh) * 0.5 + stereo(pad, 4.0) * 0.9)
mix *= (env(0, 0.25))[:, None]
mix /= np.abs(mix).max() / 0.89
wavfile.write(sys.argv[1], SR, (mix * 32767).astype(np.int16))
print("WROTE", sys.argv[1], DUR, "s")
