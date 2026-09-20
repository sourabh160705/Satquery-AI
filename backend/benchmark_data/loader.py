import os
import io
import numpy as np
import tifffile
from PIL import Image

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_sample_scenes():
    """
    Generates synthetic realistic Remote Sensing benchmark scenes
    (Single optical, Bi-temporal pair, Optical-SAR pair) for instant demonstration.
    """
    os.makedirs(BENCHMARK_DIR, exist_ok=True)
    h, w = 512, 512

    # 1. Single Optical Scene (Sentinel-2 / BigEarthNet style: River, Forest, Urban cluster)
    scene_optical_path = os.path.join(BENCHMARK_DIR, "sample_sentinel2_optical.tif")
    if not os.path.exists(scene_optical_path):
        opt = np.zeros((h, w, 3), dtype=np.uint8)
        # Background: Green vegetation / cropland
        opt[..., 0] = 50 + (np.sin(np.linspace(0, 20, h))[:, None] * 15).astype(np.uint8)
        opt[..., 1] = 160 + (np.cos(np.linspace(0, 15, w))[None, :] * 20).astype(np.uint8)
        opt[..., 2] = 45

        # Winding River (Blue)
        x = np.arange(w)
        y_river = (h // 2 + np.sin(x / 40.0) * 80).astype(int)
        for offset in range(-25, 26):
            y_curr = np.clip(y_river + offset, 0, h - 1)
            opt[y_curr, x] = [15, 80, 190]

        # Urban settlement cluster in top-right (grey/brick-red)
        opt[40:180, 320:470] = [170, 160, 155]
        # Some roads
        opt[100:106, :] = [210, 210, 210]
        opt[:, 390:396] = [210, 210, 210]

        tifffile.imwrite(scene_optical_path, opt)

    # 2. Bi-temporal Pair (T1: Pre-flood, T2: Post-flood / altered urban)
    t1_path = os.path.join(BENCHMARK_DIR, "bitemporal_t1_pre.tif")
    t2_path = os.path.join(BENCHMARK_DIR, "bitemporal_t2_post.tif")
    if not os.path.exists(t1_path) or not os.path.exists(t2_path):
        t1 = np.copy(opt) if 'opt' in locals() else np.zeros((h, w, 3), dtype=np.uint8)
        t2 = np.copy(t1)

        # In T2, river expands (flood inundation)
        x = np.arange(w)
        y_river = (h // 2 + np.sin(x / 40.0) * 80).astype(int)
        for offset in range(-65, 66):
            y_curr = np.clip(y_river + offset, 0, h - 1)
            t2[y_curr, x] = [10, 95, 220]

        # New construction area in bottom-left
        t2[360:460, 60:180] = [200, 185, 175]

        tifffile.imwrite(t1_path, t1)
        tifffile.imwrite(t2_path, t2)

    # 3. Optical + SAR Pair (Optical Cartosat-style + SAR RISAT-style)
    opt_pair_path = os.path.join(BENCHMARK_DIR, "pair_cartosat_optical.tif")
    sar_pair_path = os.path.join(BENCHMARK_DIR, "pair_risat_sar.tif")
    if not os.path.exists(opt_pair_path) or not os.path.exists(sar_pair_path):
        cartosat = np.copy(t1)
        # SAR scene (single-channel radar backscatter with speckle)
        rng = np.random.RandomState(42)
        speckle = rng.gamma(shape=4.0, scale=0.25, size=(h, w)).astype(np.float32)
        sar = np.full((h, w), 80, dtype=np.float32)

        # Water in SAR is very dark (specular reflection away from antenna)
        water_mask = (cartosat[..., 2] > cartosat[..., 0] + 50)
        sar[water_mask] = 15.0

        # Built-up in SAR has intense double-bounce backscatter (bright return)
        urban_mask = (cartosat[..., 0] > 140) & (cartosat[..., 1] > 140)
        sar[urban_mask] = 230.0

        sar_noisy = np.clip(sar * speckle, 0, 255).astype(np.uint8)

        tifffile.imwrite(opt_pair_path, cartosat)
        tifffile.imwrite(sar_pair_path, sar_noisy)

if __name__ == "__main__":
    generate_sample_scenes()
    print("Benchmark sample datasets generated successfully.")
