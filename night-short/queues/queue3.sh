#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
for p in ns_back_s11 ns_back_chain ns_close_s11 ns_close_s12 i2v_front_s12; do python3 upclip.py $p >> logs/up.log 2>&1; done
