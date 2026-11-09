"""Block D step 2: Wan2.2-Animate-14B Q3_K_M (GGUF) + lightx2v 4-step LoRA, portrait reference driven by a talking-head video.

Usage: ~/miniconda3/envs/comfy/bin/python gen_animate.py <label> [--w 320 --h 576 --frames 21 --steps 4 --no-pose --seed 42]
Outputs -> out/<label>_*.png, timings -> animate.log. Pose/face images are computed in the same graph.
"""
import argparse, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "style-ladder"))
import gen as sl  # noqa

ap = argparse.ArgumentParser()
ap.add_argument("label")
ap.add_argument("--w", type=int, default=320)
ap.add_argument("--h", type=int, default=576)
ap.add_argument("--frames", type=int, default=21)
ap.add_argument("--steps", type=int, default=4)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--no-pose", action="store_true")
ap.add_argument("--no-retarget", action="store_true")
ap.add_argument("--ref", default="vb_ref_portrait.png")
a = ap.parse_args()
W, H, N = a.w, a.h, a.frames
resize = lambda src: {"class_type": "ImageResizeKJv2", "inputs": {"image": src, "width": W, "height": H, "upscale_method": "lanczos", "keep_proportion": "crop",
                                                                 "pad_color": "0, 0, 0", "crop_position": "center", "divisible_by": 16}}
pf = {"model": ["det", 0], "images": ["drv", 0], "width": W, "height": H}
if not a.no_retarget:
    pf["retarget_image"] = ["ref", 0]
wa = {"positive": ["pos", 0], "negative": ["neg", 0], "vae": ["vae", 0], "width": W, "height": H, "length": N, "batch_size": 1,
      "continue_motion_max_frames": 5, "video_frame_offset": 0, "clip_vision_output": ["cve", 0], "reference_image": ["ref", 0], "face_video": ["pf", 1]}
if not a.no_pose:
    wa["pose_video"] = ["pose", 0]
g = {
    "det": {"class_type": "OnnxDetectionModelLoader", "inputs": {"vitpose_model": "vitpose-l-wholebody.onnx", "yolo_model": "yolov10m.onnx", "onnx_device": "CUDAExecutionProvider"}},
    "vid": {"class_type": "VHS_LoadVideo", "inputs": {"video": "driving_10-15s.mp4", "force_rate": 16, "custom_width": 0, "custom_height": 0, "frame_load_cap": N,
                                                      "skip_first_frames": 0, "select_every_nth": 1, "format": "AnimateDiff"}},
    "drv": resize(["vid", 0]),
    "ref0": {"class_type": "LoadImage", "inputs": {"image": a.ref}},
    "ref": resize(["ref0", 0]),
    "pf": {"class_type": "PoseAndFaceDetection", "inputs": pf},
    "pose": {"class_type": "DrawViTPose", "inputs": {"pose_data": ["pf", 0], "width": W, "height": H, "retarget_padding": 0 if a.no_retarget else 16,
                                                    "body_stick_width": -1, "hand_stick_width": -1, "draw_head": True}},
    "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-Animate-14B-Q3_K_M.gguf"}},
    "lora": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet", 0], "lora_name": "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors", "strength_model": 1.2}},
    "ms": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["lora", 0], "shift": 5}},
    "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
    "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": "a young woman with short black bob hair and a red jacket talking naturally to the camera, soft smile, blurred cobblestone street, warm sunlight"}},
    "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": "blurry, static, worst quality, deformed face, extra fingers, jittery, watermark, text"}},
    "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
    "cvl": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
    "cve": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["cvl", 0], "image": ["ref", 0], "crop": "none"}},
    "wa": {"class_type": "WanAnimateToVideo", "inputs": wa},
    "guider": {"class_type": "CFGGuider", "inputs": {"model": ["ms", 0], "positive": ["wa", 0], "negative": ["wa", 1], "cfg": 1}},
    "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": a.seed}},
    "smp": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}},
    "sig": {"class_type": "BasicScheduler", "inputs": {"model": ["ms", 0], "scheduler": "simple", "steps": a.steps, "denoise": 1}},
    "sca": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["smp", 0], "sigmas": ["sig", 0], "latent_image": ["wa", 2]}},
    "trim": {"class_type": "TrimVideoLatent", "inputs": {"samples": ["sca", 0], "trim_amount": ["wa", 3]}},
    "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["trim", 0], "vae": ["vae", 0]}},
    "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": f"vb_animate/gen_{a.label}"}},
}
peak = sl.Peak()
files, dt = sl.run(g)
mem = peak.stop()
out = Path(__file__).resolve().parent / "out"
out.mkdir(exist_ok=True)
for f in files:
    shutil.copy(f, out / f.name)
line = f"{time.strftime('%H:%M:%S')} animate {a.label} {W}x{H} {N}f {a.steps}steps pose={not a.no_pose} retarget={not a.no_retarget} {dt:.0f}s {mem} files={len(files)}"
print(line, flush=True)
open(Path(__file__).resolve().parent / "animate.log", "a").write(line + "\n")
