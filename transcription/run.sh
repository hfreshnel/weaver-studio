#!/usr/bin/env bash
# Expose pip-installed cuBLAS/cuDNN to ctranslate2, then run the transcription.
cd "$(dirname "$0")"
SP=$(.venv/bin/python -c "import site; print(site.getsitepackages()[0])")
export LD_LIBRARY_PATH="$SP/nvidia/cublas/lib:$SP/nvidia/cudnn/lib:$LD_LIBRARY_PATH"
exec .venv/bin/python transcribe.py "$@"
