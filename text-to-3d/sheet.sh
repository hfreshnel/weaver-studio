#!/usr/bin/env bash
# Contact sheet of a GLB: row 1 = textured views, row 2 = wireframe.
# Usage: ./sheet.sh <in.glb> [size=512]  ->  sheets/<parent>_<name>.jpg
set -euo pipefail
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
PY=~/miniconda3/envs/comfy/bin/python
DIR="$(cd "$(dirname "$0")" && pwd)"
in="$(realpath "$1")"; size="${2:-512}"
mkdir -p "$DIR/sheets"
tmp="$(mktemp -d -p "$DIR/sheets")"
"$BLENDER" -b --factory-startup --python "$(wslpath -w "$DIR/render.py")" -- "$(wslpath -w "$in")" "$(wslpath -w "$tmp")\\v" "$size" > "$tmp/log" 2>&1 \
  || { tail -20 "$tmp/log"; exit 1; }
out="$DIR/sheets/$(basename "$(dirname "$in")")_$(basename "${in%.glb}").jpg"
$PY -I -c "
import sys
from PIL import Image
t, s, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
sheet = Image.new('RGB', (4 * s, 2 * s))
for r, k in enumerate(('tex', 'wire')):
    for i in range(4):
        sheet.paste(Image.open(f'{t}/v_{k}{i}.png').convert('RGB'), (i * s, r * s))
sheet.save(out, quality=90)
" "$tmp" "$size" "$out"
rm -rf "$tmp"
echo "$out"
