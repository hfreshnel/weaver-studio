#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
sleep 30; while pgrep -f "queue15.sh" > /dev/null; do sleep 5; done
G=", static camera, solid green background stays flat and unchanged, anime style"
python3 w.py zfront_chain ns_zfront_last.png "the girl keeps walking slowly towards the camera with a calm natural walking cycle, arms hanging and swinging gently by her sides, hands relaxed, face calm, hair and skirt moving$G" --seed 33 > logs/zfront_chain.log 2>&1
python3 upclip.py ns_zfront_chain >> logs/up.log 2>&1
