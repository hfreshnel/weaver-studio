#!/bin/bash
cd /home/freshnel/dev/git/night-short
sleep 40; while pgrep -f "queue15.sh|queue19.sh|queue18.sh" > /dev/null; do sleep 5; done
for s in 41 42; do ./zjob.sh zclose ns_zclose.png $s 512x752 125 "close-up of the girl's face, she blinks softly and smiles slightly, her head tilts gently, hair and red ribbon move slightly in a light breeze"; done
