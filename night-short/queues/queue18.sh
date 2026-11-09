#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
for sh in close2 back2 mid2; do python3 zk.py $sh 81 82 83 84 > logs/zk_$sh.log 2>&1; done
