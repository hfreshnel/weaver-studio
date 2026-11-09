#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
G=", static camera, solid green background stays flat and unchanged, anime style"
for s in 13 14; do
python3 w.py front_s$s ns_front_pad.png "the girl walks very slowly and calmly towards the camera with a gentle walking cycle, she approaches only a little, eyes stay amber, arms swinging gently, hair and skirt moving$G" --seed $s > logs/front_s$s.log 2>&1
python3 upclip.py ns_front_s$s >> logs/up.log 2>&1
done
