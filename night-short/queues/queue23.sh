#!/bin/bash
cd /home/freshnel/dev/git/night-short
sleep 90; while pgrep -f "queue21.sh|queue22.sh|queue19.sh" > /dev/null; do sleep 5; done
for s in 61 62; do ./zjob.sh zmid ns_zmid.png $s 512x752 125 "the girl looks up at the sky with a gentle smile, her head tilts slightly, hair and red ribbon move in a light breeze, calm and graceful, no objects, clean empty background"; done
