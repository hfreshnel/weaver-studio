#!/usr/bin/env bash
# Usage: [BENCH=script.py] ./bench_cache.sh <label> <comfyui flags...>
# Starts ComfyUI with the given flags, samples RAM/swap/VRAM/RSS every 2 s, runs $BENCH (default bench_cache.py), stops the server.
set -u
label=$1; shift
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$here/bench"
source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate comfy
cd "$here/../comfyui"
python main.py "$@" > "$here/bench/$label.server.log" 2>&1 &
srv=$!
until curl -sf http://127.0.0.1:8188/system_stats > /dev/null; do sleep 1; kill -0 $srv 2>/dev/null || { echo "server died"; exit 1; }; done
( echo "t,ram_used_mb,swap_used_mb,vram_mb,rss_mb"
  while kill -0 $srv 2>/dev/null; do
    read -r ram swap < <(free -m | awk '/Mem:/{r=$3} /Swap:/{s=$3} END{print r, s}')
    vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    rss_kb=$(awk '/VmRSS/{print $2}' /proc/$srv/status 2>/dev/null); rss=$(( ${rss_kb:-0} / 1024 ))
    echo "$(date +%s),$ram,$swap,$vram,$rss"; sleep 2
  done ) > "$here/bench/$label.mem.csv" &
t0=$(date +%s)
python3 "$here/${BENCH:-bench_cache.py}" "$label"
echo "total $(( $(date +%s) - t0 )) s"
kill $srv; wait $srv 2>/dev/null || true
