#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
G=", static camera, solid green background stays flat and unchanged, anime style"
for s in 17 18; do
python3 w.py frontL_s$s ns_front_pad2.png "the girl walks slowly towards the camera with a calm natural walking cycle, arms hanging and swinging gently by her sides, hands relaxed, face calm, hair and skirt moving$G" --seed $s > logs/frontL_s$s.log 2>&1
python3 upclip.py ns_frontL_s$s >> logs/up.log 2>&1
done
