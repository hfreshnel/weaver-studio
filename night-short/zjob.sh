#!/bin/bash
# usage: zjob.sh <name> <image> <seed> <size> <hue> "<prompt>"   -> Wan, x2 upscale, matting, despill
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
G=", static camera, solid green background stays flat and unchanged, anime style"
python3 w.py $1_s$3 $2 "$6$G" --seed $3 --size $4 > logs/$1_s$3.log 2>&1
python3 upclip.py ns_$1_s$3 >> logs/up.log 2>&1
conda activate matting; python -I layer.py x2/ns_$1_s$3 layers/$1_s$3_x2 >> logs/mat.log 2>&1
conda activate comfy; python despill2.py layers/$1_s$3_x2 $5 30 >> logs/mat.log 2>&1
