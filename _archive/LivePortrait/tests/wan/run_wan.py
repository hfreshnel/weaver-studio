"""Rendu Wan2.2-Animate-14B (mode animation) via l'API d'un serveur ComfyUI local.

Usage : python run_wan.py semireal [photoreal chibi ...] [--quant Q4_K_M] [--frames 77] [--no-retarget]
Le serveur doit tourner : cd ~/dev/git/ComfyUI && python main.py --lowvram
"""
import argparse
import json
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
COMFY = Path.home() / "dev/git/ComfyUI"
OUT_DIR = Path(__file__).parent / "out"
DRIVING = "driving_10-15s.mp4"
W, H, FPS = 480, 576, 16

STYLE = {
    "photoreal": "photorealistic portrait photo",
    "semireal": "stylized 3D animated movie character, soft render",
    "chibi": "2D cartoon illustration, flat colors, clean lineart",
}


def build_prompt(char, quant, frames, retarget, seed):
    text = (f"a man with glasses talking to the camera, natural facial expressions and head movement, "
            f"{STYLE.get(char, '')}, plain background")
    p = {
        # Entrées
        "ref_load": {"class_type": "LoadImage", "inputs": {"image": f"{char}.png"}},
        "ref": {"class_type": "ImageResizeKJv2", "inputs": {
            "image": ["ref_load", 0], "width": W, "height": H, "upscale_method": "lanczos",
            "keep_proportion": "pad_edge_pixel", "pad_color": "0, 0, 0", "crop_position": "center",
            "divisible_by": 16}},
        "video": {"class_type": "VHS_LoadVideo", "inputs": {
            "video": DRIVING, "force_rate": FPS, "custom_width": 0, "custom_height": 0,
            "frame_load_cap": frames, "skip_first_frames": 0, "select_every_nth": 1}},
        # Prétraitement pose + visage
        "det": {"class_type": "OnnxDetectionModelLoader", "inputs": {
            "vitpose_model": "vitpose-l-wholebody.onnx", "yolo_model": "yolov10m.onnx",
            "onnx_device": "CUDAExecutionProvider"}},
        "pose": {"class_type": "PoseAndFaceDetection", "inputs": {
            "model": ["det", 0], "images": ["video", 0], "width": W, "height": H,
            **({"retarget_image": ["ref", 0]} if retarget else {})}},
        "pose_img": {"class_type": "DrawViTPose", "inputs": {
            "pose_data": ["pose", 0], "width": W, "height": H, "retarget_padding": 16,
            "body_stick_width": -1, "hand_stick_width": -1, "draw_head": True}},
        # Modèles
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": f"Wan2.2-Animate-14B-{quant}.gguf"}},
        "lora": {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["unet", 0], "strength_model": 1.2,
            "lora_name": "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"}},
        "clip": {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": "umt5-xxl-encoder-Q5_K_M.gguf", "type": "wan"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "cvis": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
        "cvis_enc": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["cvis", 0], "image": ["ref", 0], "crop": "none"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": text}},
        "neg": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["pos", 0]}},
        # Génération
        "wan": {"class_type": "WanAnimateToVideo", "inputs": {
            "positive": ["pos", 0], "negative": ["neg", 0], "vae": ["vae", 0],
            "width": W, "height": H, "length": frames, "batch_size": 1,
            "continue_motion_max_frames": 5, "video_frame_offset": 0,
            "clip_vision_output": ["cvis_enc", 0], "reference_image": ["ref", 0],
            "face_video": ["pose", 1], "pose_video": ["pose_img", 0]}},
        "guider": {"class_type": "CFGGuider", "inputs": {"model": ["lora", 0], "positive": ["wan", 0], "negative": ["wan", 1], "cfg": 1.0}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {"model": ["lora", 0], "scheduler": "simple", "steps": 4, "denoise": 1.0}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0],
            "sigmas": ["sigmas", 0], "latent_image": ["wan", 2]}},
        "trim": {"class_type": "TrimVideoLatent", "inputs": {"samples": ["sample", 0], "trim_amount": ["wan", 3]}},
        "decode": {"class_type": "VAEDecodeTiled", "inputs": {
            "samples": ["trim", 0], "vae": ["vae", 0], "tile_size": 256, "overlap": 64,
            "temporal_size": 32, "temporal_overlap": 8}},
    }
    for name, images in (("save", ["decode", 0]), ("save_pose", ["pose_img", 0])):
        p[name] = {"class_type": "VHS_VideoCombine", "inputs": {
            "images": images, "frame_rate": FPS, "loop_count": 0, "filename_prefix": f"wan_{char}_{name}",
            "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 17, "save_metadata": False,
            "trim_to_audio": False, "pingpong": False, "save_output": True}}
    return p


def api(path, data=None):
    req = urllib.request.Request(SERVER + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


class MemWatch(threading.Thread):
    """Relève le pic de VRAM (nvidia-smi) et de RAM utilisée (WSL) pendant le rendu."""

    def __init__(self):
        super().__init__(daemon=True)
        self.vram = self.ram = 0
        self.stop = False

    def run(self):
        while not self.stop:
            try:
                v = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True).stdout
                self.vram = max(self.vram, int(v.strip().splitlines()[0]))
                m = dict(l.split(":") for l in Path("/proc/meminfo").read_text().splitlines())
                used = int(m["MemTotal"].split()[0]) - int(m["MemAvailable"].split()[0])
                self.ram = max(self.ram, used // 1024)
            except Exception:
                pass
            time.sleep(2)


def render(char, args):
    prompt = build_prompt(char, args.quant, args.frames, not args.no_retarget, args.seed)
    pid = api("/prompt", {"prompt": prompt})["prompt_id"]
    watch = MemWatch()
    watch.start()
    t0 = time.time()
    print(f"[{char}] lancé ({pid}), {args.quant}, {args.frames} images", flush=True)
    while True:
        time.sleep(5)
        h = api(f"/history/{pid}").get(pid)
        if h and h.get("status", {}).get("completed") is not None or (h and h["status"].get("status_str") == "error"):
            break
    watch.stop = True
    dt = time.time() - t0
    status = h["status"]
    if status.get("status_str") != "success":
        errs = [m for m in status.get("messages", []) if m[0] == "execution_error"]
        print(f"[{char}] ÉCHEC après {dt/60:.1f} min : {json.dumps(errs)[:1500]}")
        return False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for node, suffix in (("save", ""), ("save_pose", "_pose")):
        f = h["outputs"][node]["gifs"][0]
        src = COMFY / "output" / f.get("subfolder", "") / f["filename"]
        shutil.copy(src, OUT_DIR / f"{char}{suffix}.mp4")
    line = (f"{char}: {dt/60:.1f} min, {args.quant}, {args.frames} images {W}x{H}, "
            f"pic VRAM {watch.vram} Mo, pic RAM WSL {watch.ram} Mo, retarget={not args.no_retarget}")
    print(f"[{char}] OK : {line}")
    with open(OUT_DIR / "timings.txt", "a") as fh:
        fh.write(line + "\n")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("chars", nargs="+")
    ap.add_argument("--quant", default="Q4_K_M")
    ap.add_argument("--frames", type=int, default=77)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-retarget", action="store_true")
    a = ap.parse_args()
    for c in a.chars:
        render(c, a)
