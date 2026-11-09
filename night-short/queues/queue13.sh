#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
sleep 20; while pgrep -f "queue10.sh|queue11.sh" > /dev/null; do sleep 5; done
G=", static camera, solid green background stays flat and unchanged, anime style"
for s in 12 13; do
python3 w.py mid_s$s ns_mid.png "the girl looks up at the sky with a gentle smile, her head tilts slightly, hair and red ribbon move in a light breeze, calm and graceful, no objects, clean empty background$G" --seed $s > logs/mid_s$s.log 2>&1
python3 upclip.py ns_mid_s$s >> logs/up.log 2>&1
done
