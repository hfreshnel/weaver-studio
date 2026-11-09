#!/usr/bin/env bash
# Planche côte à côte : conduite | LivePortrait | Wan-Animate, sur l'extrait 10-15 s, avec le son d'origine.
# Usage : ./compare.sh semireal [photoreal chibi]
set -euo pipefail
cd "$(dirname "$0")"
DRIVE=~/dev/git/ComfyUI/input/driving_10-15s.mp4
START=10          # secondes dans tests/driving.mp4
SRC_FPS=24.92     # cadence réelle de tests/driving.mp4 (299/12)

for c in "$@"; do
  wan=out/$c.mp4
  n=$(ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$wan")
  dur=$(python3 -c "print($n/16)")
  # LivePortrait a écrit une image par image source, mais à 24 fps : on prend les mêmes images source.
  first=$(python3 -c "print(round($START*$SRC_FPS))")
  count=$(python3 -c "print(round($dur*$SRC_FPS))")
  ffmpeg -v error -y -i "$DRIVE" -i ../out2/$c/$c--driving.mp4 -i "$wan" -ss $START -t "$dur" -i ../driving.mp4 \
    -filter_complex "\
[0:v]trim=end_frame=$n,setpts=PTS-STARTPTS,scale=480:576,drawtext=text='toi':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[a];\
[1:v]trim=start_frame=$first:end_frame=$((first+count)),setpts=(PTS-STARTPTS)*$n/16/($count/24),fps=16,scale=480:576,drawtext=text='LivePortrait':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[b];\
[2:v]scale=480:576,drawtext=text='Wan-Animate':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[w];\
[a][b][w]hstack=3[v]" \
    -map "[v]" -map 3:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -shortest compare_$c.mp4
  echo "compare_$c.mp4"
done
