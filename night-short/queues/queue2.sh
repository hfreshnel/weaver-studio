#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
while pgrep -f queue1.sh > /dev/null; do sleep 5; done
G=", static camera, solid green background stays flat and unchanged, anime style"
python3 w.py back_chain ns_back_s11_last.png "the girl keeps walking slowly straight away from the camera, seen from behind, getting gradually smaller as she walks into the distance, calm natural walking cycle, arms swinging gently, hair and skirt moving$G" --seed 12 > logs/back_chain.log 2>&1
python3 w.py close_s12 ns_close.png "close-up of the girl's face, she blinks softly and smiles slightly, her head tilts gently, hair and red ribbon move slightly in a light breeze$G" --seed 12 > logs/close_s12.log 2>&1
