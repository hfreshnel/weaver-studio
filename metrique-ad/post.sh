#!/usr/bin/env bash
# Upscale + 30 fps conform for every selected clip -> clips_final/<shot>/
set -e
cd "$(dirname "$0")"
PY=/home/freshnel/miniconda3/envs/comfy/bin/python
for c in P01_1001 P02_1002 P03_1003 P04_1004 P06_1006 P07_1007 P08_1008 P09_1009 P10_1010 P11_1011; do
  t0=$(date +%s); $PY upscale.py clips/$c ${c%_*}; echo "  $(( $(date +%s) - t0 ))s"
done
# P05: a figure walks into frame in the last ~0.2 s -> trimmed.
t0=$(date +%s); $PY upscale.py clips/P05_1005 P05 --trim-end 0.2; echo "  $(( $(date +%s) - t0 ))s"
