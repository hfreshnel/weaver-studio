#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
G=", static camera, solid green background stays flat and unchanged, anime style"
python3 w.py back_s11 ns_back_pad.png "the girl walks slowly straight away from the camera, seen from behind, getting gradually smaller as she walks into the distance, calm natural walking cycle, arms swinging gently, hair and skirt moving$G" --seed 11 > logs/back_s11.log 2>&1
python3 w.py close_s11 ns_close.png "close-up of the girl's face, she blinks softly and smiles slightly, her head tilts gently, hair and red ribbon move slightly in a light breeze$G" --seed 11 > logs/close_s11.log 2>&1
