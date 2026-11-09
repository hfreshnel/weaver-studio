"""Transcribe an audio file with faster-whisper.

Usage: ./run.sh <audio> [--lang fr] [--model large-v3-turbo] [--out outputs]
Writes <name>.txt (plain), <name>.timestamps.txt and <name>.srt.
"""
import argparse
import subprocess
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


def load_audio(path, sr=16000):
    # Decode with system ffmpeg: the PyAV build pulled by faster-whisper is API-incompatible.
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def fmt(t, sep="."):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int((s % 1) * 1000):03d}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--lang", default="fr")
    p.add_argument("--model", default="large-v3-turbo")
    p.add_argument("--compute-type", default="int8_float16")
    p.add_argument("--out", default="outputs")
    # Long recordings can drift into unpunctuated fragments when each window is conditioned on the previous text.
    p.add_argument("--no-condition", action="store_true", help="condition_on_previous_text=False")
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / Path(args.audio).stem

    t0 = time.time()
    model = WhisperModel(args.model, device="cuda", compute_type=args.compute_type)
    print(f"model loaded in {time.time() - t0:.1f}s", flush=True)

    t1 = time.time()
    segments, info = model.transcribe(
        load_audio(args.audio), language=args.lang, beam_size=5, vad_filter=True,
        condition_on_previous_text=not args.no_condition,
    )
    print(f"audio duration: {info.duration:.0f}s", flush=True)

    with open(f"{stem}.txt", "w") as plain, open(f"{stem}.timestamps.txt", "w") as ts, open(f"{stem}.srt", "w") as srt:
        for i, seg in enumerate(segments, 1):
            text = seg.text.strip()
            plain.write(text + "\n")
            ts.write(f"[{fmt(seg.start)[:8]}] {text}\n")
            srt.write(f"{i}\n{fmt(seg.start, ',')} --> {fmt(seg.end, ',')}\n{text}\n\n")
            print(f"[{fmt(seg.start)[:8]}] {text}", flush=True)

    print(f"transcription done in {time.time() - t1:.1f}s -> {stem}.*", flush=True)


if __name__ == "__main__":
    main()
