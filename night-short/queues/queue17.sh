#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
for sh in close back mid; do python3 zk.py $sh > logs/zk_$sh.log 2>&1; done
