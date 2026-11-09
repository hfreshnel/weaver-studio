"""Print new ComfyUI log lines about model loads, finished samplers, errors and prompt completion (stdlib only).

Usage: python3 watch.py [--interval 20]   # exits when the ComfyUI queue is empty
"""
import argparse, json, time, urllib.request

API = "http://127.0.0.1:8188"
KEYS = ("got prompt", "Requested to load", "100%", "ERROR", "out of memory", "executed in")


def get(path):
    return json.load(urllib.request.urlopen(f"{API}{path}"))


ap = argparse.ArgumentParser()
ap.add_argument("--interval", type=int, default=20)
a = ap.parse_args()
# The server keeps a rolling buffer of log entries: track entries already seen by (timestamp, text).
seen = {(e["t"], e["m"]) for e in get("/internal/logs/raw")["entries"]}
while True:
    time.sleep(a.interval)
    entries = get("/internal/logs/raw")["entries"]
    new = [e for e in entries if (e["t"], e["m"]) not in seen]
    seen.update((e["t"], e["m"]) for e in new)
    for line in "".join(e["m"] for e in new).replace("\r", "\n").splitlines():
        if any(k in line for k in KEYS) and not line.startswith(" "):
            print(f"{time.strftime('%H:%M:%S')} {line.strip()[-160:]}", flush=True)
    q = get("/queue")
    if not q["queue_running"] and not q["queue_pending"]:
        print("queue empty", flush=True)
        break
