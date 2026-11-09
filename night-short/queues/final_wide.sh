#!/bin/bash
source /home/freshnel/miniconda3/etc/profile.d/conda.sh; conda activate comfy
cd /home/freshnel/dev/git/night-short
export NS_F=1.5
python cycle.py layers/frontL_s17_x2 s2L_hd --period 32 --start 12 --frames 72 --start-feet 1000 --rate -0.08 --petals 24
python cycle.py layers/back_s11_x2 s4c_hd --period 30 --start 6 --frames 120 --petals 24
python zoomshot.py s4c_hd s4z_hd 1.0 1.12
