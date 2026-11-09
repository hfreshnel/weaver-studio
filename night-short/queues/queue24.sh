#!/bin/bash
cd /home/freshnel/dev/git/night-short
sleep 30; while pgrep -f "queue23.sh" > /dev/null; do sleep 5; done
./zjob.sh zbackchain ns_zback_last.png 53 512x752 125 "the girl keeps walking slowly straight away from the camera, seen from behind, getting gradually smaller as she walks into the distance, calm natural walking cycle, arms swinging gently, hair and skirt moving"
