"""Compare Wan 2.2 TI2V 5B fp16 vs GGUF Q8_0 (and umt5 GGUF Q5) on the webtoon green-screen clip (stdlib only).

Usage: [MODE=compare|steady] python3 bench_wan_quant.py <label>
compare (default): fp16 / Q8 / fp16 / Q8 / Q8+TE-Q5, same seed and input.
steady: three consecutive Q8 jobs (seeds 7, 8, 9), as in a real Q8-only session.
Writes bench/<label>.json.
"""
import json, os, sys, time
from pathlib import Path

from bench_cache import ROOT, run, wan_i2v

UNET_Q8 = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}}
TE_Q5 = {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": "umt5-xxl-encoder-Q5_K_M.gguf", "type": "wan"}}


def variant(unet_q8, te_q5, prefix, seed=7):
    g = wan_i2v(seed, 49, prefix)
    if unet_q8:
        g["1"] = UNET_Q8
    if te_q5:
        g["2"] = TE_Q5
    return g


def main():
    label = sys.argv[1]
    p = f"bench_{label}/"
    if os.environ.get("MODE") == "steady":
        jobs = [(f"q8_s{s}", variant(True, False, p + f"q8_s{s}", s)) for s in (7, 8, 9)]
    else:
        jobs = [
            ("fp16_1", variant(False, False, p + "fp16_1")),
            ("q8_1", variant(True, False, p + "q8_1")),
            ("fp16_2", variant(False, False, p + "fp16_2")),
            ("q8_2", variant(True, False, p + "q8_2")),
            ("q8_teq5", variant(True, True, p + "q8_teq5")),
        ]
    out = ROOT / "bench" / f"{label}.json"
    out.parent.mkdir(exist_ok=True)
    results = []
    for name, g in jobs:
        r = run(g)
        r["job"], r["t_end"] = name, round(time.time(), 1)
        results.append(r)
        print(f"{name:10s} {r['status']:8s} {r['seconds']:7.1f} s", flush=True)
        out.write_text(json.dumps(results, indent=1))
        if r["status"] == "error":
            print(json.dumps(r["error"])[:3000])
            break


if __name__ == "__main__":
    main()
