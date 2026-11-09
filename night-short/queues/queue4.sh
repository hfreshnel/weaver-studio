#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
G=", static camera, solid green background stays flat and unchanged, anime style"
python3 w.py mid_s11 ns_mid.png "the girl looks up at falling cherry blossom petals with a gentle smile, her head tilts slightly, hair and red ribbon move in a light breeze, calm and graceful$G" --seed 11 > logs/mid_s11.log 2>&1
python3 upclip.py ns_mid_s11 >> logs/up.log 2>&1
