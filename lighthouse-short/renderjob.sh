#!/bin/bash
# GPU slot for Blender: wait for an empty ComfyUI queue, free its VRAM, render S1/S4 at Wan size, then queue Wan v2v.
cd /home/freshnel/dev/git/lighthouse-short
B=tools/blender-5.2.3-linux-x64/blender
q() { curl -s localhost:8188/queue | python3 -c "import json,sys; q=json.load(sys.stdin); print(len(q['queue_running'])+len(q['queue_pending']))"; }
until [ "$(q)" = "0" ]; do sleep 5; done
curl -s -X POST localhost:8188/free -H 'Content-Type: application/json' -d '{"unload_models": true, "free_memory": true}'; sleep 3
echo "$(date +%T) render start"
$B -b renders/lh_v2.blend --python render.py -- CamS1 1 61 $PWD/renders/s1_576 1024x576 48 GPU 2>&1 | grep -E "FRAME|Error|Traceback"
$B -b renders/lh_v2.blend --python render.py -- CamS4 101 173 $PWD/renders/s4_576 1024x576 48 GPU 2>&1 | grep -E "FRAME|Error|Traceback"
echo "$(date +%T) render end"
P1="3D animated film, cinematic CGI. Night storm at sea: a white lighthouse with a red band, its lamp dark, on a black rocky headland with a small keeper's cottage with warm windows. Huge dark waves roll and crash on the rocks with white spray and foam, heavy rain, dark storm clouds moving, slow camera push in."
P4="3D animated film, cinematic CGI. Night storm: a small red fishing boat with a white wheelhouse rocks on big dark waves in the foreground with sea spray; on the black rocky headland behind it, the white and red lighthouse shines a powerful rotating beam of light through the rain and fog, dark storm clouds."
for d in 0.35 0.5; do
  python3 v2v.py s1 $PWD/renders/s1_576 "$P1" $d --frames 61
  python3 v2v.py s4 $PWD/renders/s4_576 "$P4" $d --frames 73
done
echo "$(date +%T) v2v end"
