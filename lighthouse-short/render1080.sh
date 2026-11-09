#!/bin/bash
cd /home/freshnel/dev/git/lighthouse-short
B=tools/blender-5.2.3-linux-x64/blender
echo "$(date +%T) S4 start"
$B -b renders/lh_v4.blend --python render.py -- CamS4 101 172 $PWD/renders/s4_1080 100 40 GPU 2>&1 | grep --line-buffered -E "FRAME|Traceback"
echo "$(date +%T) S1 start"
$B -b renders/lh_v4.blend --python render.py -- CamS1 1 60 $PWD/renders/s1_1080 100 40 GPU 2>&1 | grep --line-buffered -E "FRAME|Traceback"
echo "$(date +%T) end"
