#!/bin/bash
# v3 scene: wait for upscales, free ComfyUI VRAM, render S1/S4 at Wan size, then Wan v2v of S4 at two strengths.
cd /home/freshnel/dev/git/lighthouse-short
B=tools/blender-5.2.3-linux-x64/blender
q() { curl -s localhost:8188/queue | python3 -c "import json,sys; q=json.load(sys.stdin); print(len(q['queue_running'])+len(q['queue_pending']))"; }
while pgrep -f "up.py lhw" >/dev/null || [ "$(q)" != "0" ]; do sleep 5; done
curl -s -X POST localhost:8188/free -H 'Content-Type: application/json' -d '{"unload_models": true, "free_memory": true}'; sleep 3
echo "$(date +%T) render v3 start"
$B -b renders/lh_v3.blend --python render.py -- CamS1 1 61 $PWD/renders/s1v3_576 1024x576 48 GPU 2>&1 | grep --line-buffered -E "FRAME|Traceback"
$B -b renders/lh_v3.blend --python render.py -- CamS4 101 173 $PWD/renders/s4v3_576 1024x576 48 GPU 2>&1 | grep --line-buffered -E "FRAME|Traceback"
echo "$(date +%T) render v3 end"
P4="3D animated film, cinematic CGI. Night storm: a small red fishing boat with a white wheelhouse rocks on big dark waves in the foreground with sea spray; on the black rocky headland behind it, the white and red lighthouse shines a powerful rotating beam of light through the rain and fog, dark storm clouds."
python3 v2v.py s4v3 $PWD/renders/s4v3_576 "$P4" 0.35 --frames 73
python3 v2v.py s4v3 $PWD/renders/s4v3_576 "$P4" 0.5 --frames 73
echo "$(date +%T) v2v end"
