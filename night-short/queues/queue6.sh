#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate matting
cd /home/freshnel/dev/git/night-short
for p in ns_front_s13 ns_front_s14; do
  until grep -q "^$p 49 frames" logs/up.log; do sleep 10; done
  python -I layer.py x2/$p layers/${p#ns_}_x2 >> logs/mat.log 2>&1
done
