"""Low-VRAM patch for the native TRELLIS.2 shape/texture VAE (no nodes, patch applied at import).

At 1024^3 the SparseConvNeXtBlock3d MLP expands every sparse voxel to 4x channels in one go
(~3 GB on a single tensor), which OOMs a 6 GB GPU. Run the MLP over row chunks instead and write
the result back in place: identical output, peak memory bounded by TRELLIS2_MLP_CHUNK rows.
"""
import logging
import os

from comfy.ldm.trellis2 import vae

CHUNK = int(os.environ.get("TRELLIS2_MLP_CHUNK", 1 << 18))


def _forward(self, x):
    h = self.conv(x)
    f = self.norm(h.feats)
    for i in range(0, f.shape[0], CHUNK):
        f[i:i + CHUNK] = self.mlp(f[i:i + CHUNK])
    f.add_(x.feats.to(f))
    return h.replace(f)


vae.SparseConvNeXtBlock3d._forward = _forward
logging.info(f"trellis2_lowvram: chunked SparseConvNeXtBlock3d MLP ({CHUNK} rows)")

NODE_CLASS_MAPPINGS = {}
