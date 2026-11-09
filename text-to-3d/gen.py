"""Text -> 3D on a 6 GB GPU: FLUX.2 Klein reference image -> TRELLIS.2 or Pixal3D textured mesh (ComfyUI native nodes, stdlib only).

Usage:
  python3 gen.py <name> "<object description>" [--view high|eye] [--models trellis,pixal] [--seed 42] [--res 512] [--faces 200000]
  python3 gen.py <name> --image ref.png [...]      # skip text-to-image
Outputs -> out/<name>/ref.png, out/<name>/<model>_r<res>_s<seed>.glb, timings -> gen.log
"""
import argparse, json, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path

API = "http://127.0.0.1:8188"
COMFY = Path("/home/freshnel/dev/git/comfyui")
ROOT = Path(__file__).resolve().parent

# Image-to-3D models want one whole object, centered, flat lit, on a plain background.
REF_TEMPLATE = ("3D asset reference: {subject}. A single object, entirely visible and centered, {view}, "
                "plain light grey background, soft even studio lighting, no cast shadows, sharp focus, highly detailed.")
# Pixal3D reconstructs in the camera frame: a high camera gives a tilted mesh, an eye-level one an upright mesh.
VIEWS = {"high": "three-quarter front view",
         "eye": "three-quarter front view at eye level, camera at the object's mid-height, level horizon"}


def t2i(prompt, seed, prefix):
    """FLUX.2 Klein 4B, settings from style-ladder (4 steps, cfg 1), square 1024."""
    return {
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux-2-klein-4b-Q8_0.gguf"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b_fp8_mixed.safetensors", "type": "flux2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": prompt}},
        "neg": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["pos", 0]}},
        "guider": {"class_type": "CFGGuider", "inputs": {"model": ["unet", 0], "positive": ["pos", 0], "negative": ["neg", 0], "cfg": 1}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "sigmas": {"class_type": "Flux2Scheduler", "inputs": {"steps": 4, "width": 1024, "height": 1024}},
        "lat": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sca": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0],
                                                                  "sigmas": ["sigmas", 0], "latent_image": ["lat", 0]}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["sca", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": prefix}},
    }


def i23d(image, model, seed, res, faces, mem, prefix):
    """Mirror of the 3d_pixal3d_trellis2_image_to_model template (same samplers, CFG tweaks and bake chain)."""
    unet = {"trellis": "trellis_2_int8_convrot.safetensors", "pixal": "pixal3d_int8_convrot.safetensors"}[model]
    g = {
        "img": {"class_type": "LoadImage", "inputs": {"image": image}},
        "bgm": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}},
        "mask": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["bgm", 0], "image": ["img", 0]}},
        "crop": {"class_type": "ImageCropToMask", "inputs": {"images": ["img", 0], "masks": ["mask", 0], "width": 1024, "height": 1024,
                                                            "pad_factor": 1.1, "grow_mask": 0, "background": "#000000"}},
        "dino": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "dino_v3_L_naf_fp32.safetensors"}},
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "svae": {"class_type": "VAELoader", "inputs": {"vae_name": "trellis_2_shape_vae_bf16.safetensors"}},
        "tvae": {"class_type": "VAELoader", "inputs": {"vae_name": "trellis_2_texture_vae_bf16.safetensors"}},
        # Structure stage: 32^3 occupancy grid.
        "cfg_s": {"class_type": "CFGOverride", "inputs": {"model": ["unet", 0], "cfg": 1, "start_percent": 0.667, "end_percent": 1}},
        "rcfg_s": {"class_type": "RescaleCFG", "inputs": {"model": ["cfg_s", 0], "multiplier": 0.7}},
        "ms_s": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["rcfg_s", 0], "shift": 5}},
        "lat_s": {"class_type": "EmptyTrellis2LatentStructure", "inputs": {"batch_size": 1}},
        "ks_s": {"class_type": "KSampler", "inputs": {"model": ["ms_s", 0], "positive": ["cond", 0], "negative": ["cond", 1], "latent_image": ["lat_s", 0],
                                                      "seed": seed, "steps": 12, "cfg": 7.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1}},
        "vox": {"class_type": "VaeDecodeStructureTrellis2", "inputs": {"samples": ["ks_s", 0], "vae": ["svae", 0], "resolution": "32"}},
        # Shape stage at 512, then (res > 512) upsampled to `res`.
        "cfg_g": {"class_type": "CFGOverride", "inputs": {"model": ["unet", 0], "cfg": 1, "start_percent": 0.769, "end_percent": 1}},
        "rcfg_g": {"class_type": "RescaleCFG", "inputs": {"model": ["cfg_g", 0], "multiplier": 0.5}},
        "shape": {"class_type": "Trellis2ShapeStage", "inputs": {"positive": ["cond", 0], "negative": ["cond", 1], "voxel": ["vox", 0]}},
        "ks_g": {"class_type": "KSampler", "inputs": {"model": ["rcfg_g", 0], "positive": ["shape", 0], "negative": ["shape", 1], "latent_image": ["shape", 2],
                                                      "seed": seed, "steps": 20, "cfg": 7.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1}},
        "up": {"class_type": "Trellis2UpsampleStage", "inputs": {"positive": ["shape", 0], "negative": ["shape", 1], "shape_latent": ["ks_g", 0],
                                                                 "vae": ["svae", 0], "target_resolution": res}},
        # 6 GB: the 1024 stage OOMs with the shape VAE still resident and the default memory estimate (factor 6).
        # Unload everything first, and make ComfyUI keep more weights offloaded.
        "free_u": {"class_type": "VRAM_Debug", "inputs": {"any_input": ["up", 2], "empty_cache": True, "gc_collect": True, "unload_all_models": True}},
        "mem_g": {"class_type": "ModelMemoryUsageFactorOverride", "inputs": {"model": ["rcfg_g", 0], "memory_usage_factor": mem}},
        "mem_t": {"class_type": "ModelMemoryUsageFactorOverride", "inputs": {"model": ["unet", 0], "memory_usage_factor": mem}},
        "ks_u": {"class_type": "KSampler", "inputs": {"model": ["mem_g", 0], "positive": ["up", 0], "negative": ["up", 1], "latent_image": ["free_u", 0],
                                                      "seed": seed, "steps": 12, "cfg": 7.5, "sampler_name": "euler", "scheduler": "simple", "denoise": 1}},
        # Each VAE decode at 1024 wants ~3 GB in one block: unload the diffusion model first.
        "free_d": {"class_type": "VRAM_Debug", "inputs": {"any_input": ["ks_u", 0], "empty_cache": True, "gc_collect": True, "unload_all_models": True}},
        "mesh": {"class_type": "VaeDecodeShapeTrellis", "inputs": {"samples": ["free_d", 0], "vae": ["svae", 0]}},
        # Texture stage: PBR voxel colors on the final shape.
        "tex": {"class_type": "Trellis2TextureStage", "inputs": {"positive": ["up", 0], "negative": ["up", 1], "shape_latent": ["ks_u", 0]}},
        "ks_t": {"class_type": "KSampler", "inputs": {"model": ["mem_t", 0], "positive": ["tex", 0], "negative": ["tex", 1], "latent_image": ["tex", 2],
                                                      "seed": seed + 1, "steps": 12, "cfg": 1, "sampler_name": "euler", "scheduler": "normal", "denoise": 1}},
        "free_t": {"class_type": "VRAM_Debug", "inputs": {"any_input": ["ks_t", 0], "empty_cache": True, "gc_collect": True, "unload_all_models": True}},
        "vcol": {"class_type": "VaeDecodeTextureTrellis", "inputs": {"samples": ["free_t", 0], "vae": ["tvae", 0], "shape_subdivides": ["mesh", 1]}},
        # Clean watertight remesh -> decimate -> UV unwrap -> bake PBR + normal + AO from the raw mesh.
        "remesh": {"class_type": "RemeshMesh", "inputs": {"mesh": ["mesh", 0], "resolution": min(res, 768), "sign_mode": "udf", "sign_mode.qef": False,
                                                          "sign_mode.drop_inverted_components": False, "sign_mode.drop_enclosed_components": False,
                                                          "band": 1, "project_back": 0, "fix_poles": False, "smooth_iters": 20,
                                                          "drop_small_components": 0.01, "precluster_max_verts": 20000000}},
        "dec": {"class_type": "DecimateMesh", "inputs": {"mesh": ["remesh", 0], "target_face_count": faces, "placement_mode": "midpoint"}},
        "smooth": {"class_type": "MeshSmoothNormals", "inputs": {"mesh": ["dec", 0], "crease_angle": 180}},
        "uv": {"class_type": "UnwrapMesh", "inputs": {"mesh": ["smooth", 0], "segmenter": "pec", "resolution": 2048, "padding": 1, "weld_distance": 0.0002}},
        "bake": {"class_type": "BakeTextureFromVoxel", "inputs": {"mesh": ["uv", 0], "voxel_colors": ["vcol", 0], "reference_mesh": ["mesh", 0], "texture_size": 2048}},
        "nrm": {"class_type": "BakeNormalMapFromMesh", "inputs": {"low_poly": ["uv", 0], "high_poly": ["remesh", 0], "resolution": 2048,
                                                                  "cage_distance": 0.05, "ignore_backfaces": True}},
        "ao": {"class_type": "BakeAmbientOcclusion", "inputs": {"low_poly": ["uv", 0], "high_poly": ["remesh", 0], "resolution": 1024, "samples": 64,
                                                                "max_distance": 0.71, "strength": 1, "bias": 0.01}},
        "apply": {"class_type": "ApplyTextureToMesh", "inputs": {"mesh": ["uv", 0], "base_color": ["bake", 0], "metallic": ["bake", 1], "roughness": ["bake", 2],
                                                                 "occlusion": ["ao", 0], "normal_map": ["nrm", 0]}},
        "final": {"class_type": "MeshSmoothNormals", "inputs": {"mesh": ["apply", 0], "crease_angle": 180}},
        "save": {"class_type": "SaveGLB", "inputs": {"mesh": ["final", 0], "filename_prefix": prefix}},
    }
    if res == 512:
        # Pure 512 pipeline (no cascade): on 6 GB the 1024 shape VAE decode OOMs (one ~3 GB conv output), and it saves ~12 min.
        for k in ("up", "free_u", "mem_g", "ks_u"):
            del g[k]
        g["free_d"]["inputs"]["any_input"] = ["ks_g", 0]
        g["tex"]["inputs"].update(positive=["shape", 0], negative=["shape", 1], shape_latent=["ks_g", 0])
    if model == "trellis":
        g["cond"] = {"class_type": "Trellis2Conditioning", "inputs": {"clip_vision_model": ["dino", 0], "image": ["crop", 0]}}
    else:
        # Pixal3D is pixel-aligned: it needs the camera FOV, estimated by MoGe-2 on the cropped image.
        g["moge"] = {"class_type": "LoadMoGeModel", "inputs": {"model_name": "moge_2_vitl_normal_fp16.safetensors"}}
        g["geo"] = {"class_type": "MoGeInference", "inputs": {"moge_model": ["moge", 0], "image": ["crop", 0], "resolution_level": 9, "fov_x_degrees": 0.0,
                                                               "batch_size": 4, "force_projection": True, "apply_mask": True, "refine_steps": 3}}
        g["fov"] = {"class_type": "MoGeGeometryToFOV", "inputs": {"moge_geometry": ["geo", 0], "axis": "horizontal", "unit": "degrees"}}
        g["cond"] = {"class_type": "Pixal3DConditioning", "inputs": {"clip_vision_model": ["dino", 0], "image": ["crop", 0], "camera_angle_x": ["fov", 0]}}
    return g


class Peak:
    """Sample VRAM used, system RAM used and swap used every second; keep the max."""
    def __init__(self):
        self.vram = self.ram = self.swap = 0
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._stop.is_set():
            v = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
            m = dict(l.split(":") for l in Path("/proc/meminfo").read_text().splitlines())
            kb = lambda k: int(m[k].split()[0])
            self.vram = max(self.vram, int(v.strip() or 0))
            self.ram = max(self.ram, (kb("MemTotal") - kb("MemAvailable")) // 1024)
            self.swap = max(self.swap, (kb("SwapTotal") - kb("SwapFree")) // 1024)
            time.sleep(1)

    def stop(self):
        self._stop.set()
        return f"vram={self.vram}MiB ram={self.ram / 1024:.1f}G swap={self.swap / 1024:.1f}G"


def run(graph):
    req = urllib.request.Request(f"{API}/prompt", data=json.dumps({"prompt": graph}).encode(), headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit(f"ComfyUI rejected the graph: {e.read().decode()[:3000]}")
    t0 = time.time()
    while True:
        time.sleep(2)
        h = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
        if pid in h:
            entry = h[pid]
            if entry.get("status", {}).get("status_str") == "error":
                sys.exit(f"ComfyUI error: {json.dumps(entry['status'])[:3000]}")
            return time.time() - t0


def newest(pattern):
    return max((COMFY / "output").glob(pattern), key=lambda p: p.stat().st_mtime)


def log(line):
    print(line, flush=True)
    with open(ROOT / "gen.log", "a") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("subject", nargs="?")
    ap.add_argument("--image", help="existing reference image, skips text-to-image")
    ap.add_argument("--view", choices=list(VIEWS), default="high", help="camera of the reference image")
    ap.add_argument("--models", default="trellis,pixal")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--res", type=int, default=512, help="512 = no cascade; 1024+ = upsampled shape (template: 1536, OOMs on 6 GB)")
    ap.add_argument("--faces", type=int, default=200000, help="face count after decimation")
    ap.add_argument("--mem", type=float, default=12, help="TRELLIS.2 memory_usage_factor for the 1024+ stages (ComfyUI default: 6)")
    a = ap.parse_args()
    out = ROOT / "out" / a.name
    out.mkdir(parents=True, exist_ok=True)
    ref = out / "ref.png"
    if a.image:
        shutil.copy(a.image, ref)
    elif not ref.exists():
        if not a.subject:
            sys.exit("give a subject or --image")
        peak = Peak()
        dt = run(t2i(REF_TEMPLATE.format(subject=a.subject, view=VIEWS[a.view]), a.seed, f"text-to-3d/{a.name}_ref"))
        shutil.copy(newest(f"text-to-3d/{a.name}_ref_*.png"), ref)
        log(f"{time.strftime('%H:%M:%S')} {a.name} t2i klein view={a.view} seed={a.seed} {dt:.0f}s {peak.stop()}")
    (COMFY / "input" / "text-to-3d").mkdir(parents=True, exist_ok=True)
    shutil.copy(ref, COMFY / "input" / "text-to-3d" / f"{a.name}.png")
    for model in filter(None, a.models.split(",")):  # --models "" = reference image only
        tag = f"{model}_r{a.res}_s{a.seed}"
        peak = Peak()
        dt = run(i23d(f"text-to-3d/{a.name}.png", model, a.seed, a.res, a.faces, a.mem, f"text-to-3d/{a.name}_{tag}"))
        shutil.copy(newest(f"text-to-3d/{a.name}_{tag}_*.glb"), out / f"{tag}.glb")
        log(f"{time.strftime('%H:%M:%S')} {a.name} {tag} faces={a.faces} mem={a.mem:g} {dt:.0f}s {peak.stop()}")


if __name__ == "__main__":
    main()
