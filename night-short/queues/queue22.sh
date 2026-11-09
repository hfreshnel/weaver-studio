#!/bin/bash
cd /home/freshnel/dev/git/night-short
sleep 60; while pgrep -f "queue21.sh|queue18.sh|queue19.sh" > /dev/null; do sleep 5; done
for s in 51 52; do ./zjob.sh zback ns_zback_pad.png $s 512x752 125 "the girl walks slowly straight away from the camera, seen from behind, getting gradually smaller as she walks into the distance, calm natural walking cycle, arms swinging gently, hair and skirt moving"; done
