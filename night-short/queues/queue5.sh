#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
while pgrep -f queue4.sh > /dev/null; do sleep 5; done
G=", static camera, solid green background stays flat and unchanged, anime style"
python3 w.py front_s12 ns_front_pad.png "the girl walks slowly straight towards the camera with a calm natural walking cycle, she gets gradually closer, arms swinging gently, hair and skirt moving$G" --seed 12 > logs/front_s12.log 2>&1
python3 upclip.py ns_front_s12 >> logs/up.log 2>&1
