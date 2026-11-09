"""Block D step 1: Animate preprocessing only (pose + face crops), with and without retarget to the reference. Saves PNG previews."""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "style-ladder"))
import gen as sl  # noqa

W, H, N = 320, 576, 21
g = {
    "det": {"class_type": "OnnxDetectionModelLoader", "inputs": {"vitpose_model": "vitpose-l-wholebody.onnx", "yolo_model": "yolov10m.onnx", "onnx_device": "CUDAExecutionProvider"}},
    "vid": {"class_type": "VHS_LoadVideo", "inputs": {"video": "driving_10-15s.mp4", "force_rate": 16, "custom_width": 0, "custom_height": 0, "frame_load_cap": N,
                                                      "skip_first_frames": 0, "select_every_nth": 1, "format": "AnimateDiff"}},
    "drv": {"class_type": "ImageResizeKJv2", "inputs": {"image": ["vid", 0], "width": W, "height": H, "upscale_method": "lanczos", "keep_proportion": "crop",
                                                       "pad_color": "0, 0, 0", "crop_position": "center", "divisible_by": 16}},
    "ref0": {"class_type": "LoadImage", "inputs": {"image": "vb_ref_portrait.png"}},
    "ref": {"class_type": "ImageResizeKJv2", "inputs": {"image": ["ref0", 0], "width": W, "height": H, "upscale_method": "lanczos", "keep_proportion": "crop",
                                                       "pad_color": "0, 0, 0", "crop_position": "center", "divisible_by": 16}},
}
for tag, retarget in (("plain", False), ("retarget", True)):
    pf = {"model": ["det", 0], "images": ["drv", 0], "width": W, "height": H}
    if retarget:
        pf["retarget_image"] = ["ref", 0]
    g[f"pf_{tag}"] = {"class_type": "PoseAndFaceDetection", "inputs": pf}
    g[f"pose_{tag}"] = {"class_type": "DrawViTPose", "inputs": {"pose_data": [f"pf_{tag}", 0], "width": W, "height": H, "retarget_padding": 16 if retarget else 0,
                                                              "body_stick_width": -1, "hand_stick_width": -1, "draw_head": True}}
    g[f"save_pose_{tag}"] = {"class_type": "SaveImage", "inputs": {"images": [f"pose_{tag}", 0], "filename_prefix": f"vb_animate/pose_{tag}"}}
    g[f"save_face_{tag}"] = {"class_type": "SaveImage", "inputs": {"images": [f"pf_{tag}", 1], "filename_prefix": f"vb_animate/face_{tag}"}}
g["save_ref"] = {"class_type": "SaveImage", "inputs": {"images": ["ref", 0], "filename_prefix": "vb_animate/ref"}}
g["save_drv"] = {"class_type": "SaveImage", "inputs": {"images": ["drv", 0], "filename_prefix": "vb_animate/drv"}}
files, dt = sl.run(g)
print(f"{dt:.0f}s", len(files))
out = Path(__file__).resolve().parent / "pre"
out.mkdir(exist_ok=True)
for f in files:
    shutil.copy(f, out / f.name)
