#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate matting
cd /home/freshnel/dev/git/night-short
for p in ns_frontL_s17 ns_frontL_s18; do
  until grep -q "^$p 49 frames" logs/up.log; do sleep 10; done
  python -I layer.py x2/$p layers/${p#ns_}_x2 >> logs/mat.log 2>&1
  conda activate comfy; python despill2.py layers/${p#ns_}_x2 154 >> logs/mat.log 2>&1; conda activate matting
done
