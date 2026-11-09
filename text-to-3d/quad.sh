#!/usr/bin/env bash
# Quad retopology + PBR bake with the Windows Blender install.
# Usage: ./quad.sh <in.glb> [target_faces=8000] [texture_size=2048] [GPU|CPU bake]  (CPU while ComfyUI is busy)  ->  <in>_quad<faces>.glb + .blend
set -euo pipefail
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
DIR="$(cd "$(dirname "$0")" && pwd)"
in="$(realpath "$1")"; faces="${2:-8000}"; size="${3:-2048}"; device="${4:-GPU}"
out="${in%.glb}_quad${faces}.glb"
stats=$("$BLENDER" -b --factory-startup --python "$(wslpath -w "$DIR/quad.py")" -- \
  "$(wslpath -w "$in")" "$(wslpath -w "$out")" "$faces" "$size" "$device" 2>&1 | tee "${out%.glb}.log" | grep --line-buffered -E '^(STATS|STEP)' || true)
echo "$stats" | grep '^STEP' || true
stats=$(echo "$stats" | grep '^STATS' || true)
[ -n "$stats" ] || { echo "Blender failed, see ${out%.glb}.log" >&2; exit 1; }
line="$(date +%T) quad $(realpath --relative-to="$DIR/out" "$out") ${stats#STATS }"
echo "$line" | tee -a "$DIR/gen.log"
