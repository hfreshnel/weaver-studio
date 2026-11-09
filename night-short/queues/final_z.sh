#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
export NS_F=1.5
python shot.py layers/zback_full_x2 s4zz_hd --start-feet 1150 --petals 24
python zoomshot.py s4zz_hd s4zz_z_hd 1.0 1.10
python montage.py v4 s1_hd s2zc_hd s3az_hd s3z_hd s4zz_z_hd s5_hd
