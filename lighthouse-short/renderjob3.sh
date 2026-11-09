#!/bin/bash
# v4 scene: S4 render at Wan size, v2v 0.35, upscale S1 v3 + both S4 candidates, then v2v 0.5 (optional).
cd /home/freshnel/dev/git/lighthouse-short
B=tools/blender-5.2.3-linux-x64/blender
curl -s -X POST localhost:8188/free -H 'Content-Type: application/json' -d '{"unload_models": true, "free_memory": true}'; sleep 3
echo "$(date +%T) render v4 start"
$B -b renders/lh_v4.blend --python render.py -- CamS4 101 173 $PWD/renders/s4v4_576 1024x576 48 GPU 2>&1 | grep --line-buffered -E "FRAME|Traceback"
echo "$(date +%T) render v4 end"
P4="3D animated film, cinematic CGI. Night storm: a small red fishing boat with a white wheelhouse rocks on big dark waves in the foreground with sea spray; on the black rocky headland behind it, the white and red lighthouse shines a powerful rotating beam of light through the rain and fog, dark storm clouds."
python3 v2v.py s4v4 $PWD/renders/s4v4_576 "$P4" 0.35 --frames 73
python3 up.py renders/s1v3_576
python3 up.py renders/s4v4_576
python3 up.py lhv_s4v4_d35
echo "$(date +%T) upscales end"
python3 v2v.py s4v4 $PWD/renders/s4v4_576 "$P4" 0.5 --frames 73
python3 up.py lhv_s4v4_d50
echo "$(date +%T) all end"
