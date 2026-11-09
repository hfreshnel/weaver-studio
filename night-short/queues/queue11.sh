#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
while pgrep -f queue10.sh > /dev/null; do sleep 5; done
G=", static camera, solid green background stays flat and unchanged, anime style"
for s in 21 22; do
python3 w.py side_s$s ns_side_pad.png "the girl walks in profile from the left to the right across the frame at a steady pace with a natural walking cycle, she keeps moving forward to the right, arms swinging gently, hair and skirt moving$G" --seed $s --size 832x560 > logs/side_s$s.log 2>&1
python3 upclip.py ns_side_s$s >> logs/up.log 2>&1
done
