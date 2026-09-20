import io
import base64
import numpy as np
from PIL import Image

class SpectralEngine:
    """
    Computes remote sensing indices and converts them to colorized visual evidence overlays.
    """

    @staticmethod
    def compute_ndvi(bands: np.ndarray) -> dict:
        """NDVI: (NIR - Red) / (NIR + Red)"""
        c, h, w = bands.shape
        if c >= 4:
            nir = bands[3].astype(np.float32)
            red = bands[0].astype(np.float32)
        elif c == 3:
            # Synthetic proxy from Green vs Red if NIR is missing
            nir = bands[1].astype(np.float32) * 1.2
            red = bands[0].astype(np.float32)
        else:
            nir = bands[0].astype(np.float32)
            red = bands[0].astype(np.float32) * 0.7

        denom = nir + red + 1e-6
        ndvi = (nir - red) / denom
        ndvi = np.clip(ndvi, -1.0, 1.0)

        # Color map for NDVI: Brown (-1) -> Yellow (0) -> Lush Green (1)
        rgb = SpectralEngine._colorize_palette(ndvi, -0.2, 0.8, "vegetation")
        mean_val = float(np.mean(ndvi))
        coverage_pct = float(np.sum(ndvi > 0.3) / ndvi.size * 100)

        return {
            "index_name": "NDVI (Normalized Difference Vegetation Index)",
            "mean_score": round(mean_val, 3),
            "vegetation_coverage_pct": round(coverage_pct, 1),
            "overlay_base64": SpectralEngine._to_base64_png(rgb)
        }

    @staticmethod
    def compute_ndwi(bands: np.ndarray) -> dict:
        """NDWI: (Green - NIR) / (Green + NIR)"""
        c, h, w = bands.shape
        if c >= 4:
            green = bands[1].astype(np.float32)
            nir = bands[3].astype(np.float32)
        elif c == 3:
            green = bands[1].astype(np.float32)
            nir = bands[2].astype(np.float32) * 0.8
        else:
            green = bands[0].astype(np.float32)
            nir = bands[0].astype(np.float32) * 1.1

        denom = green + nir + 1e-6
        ndwi = (green - nir) / denom
        ndwi = np.clip(ndwi, -1.0, 1.0)

        rgb = SpectralEngine._colorize_palette(ndwi, -0.3, 0.5, "water")
        mean_val = float(np.mean(ndwi))
        water_coverage_pct = float(np.sum(ndwi > 0.1) / ndwi.size * 100)

        return {
            "index_name": "NDWI (Normalized Difference Water Index)",
            "mean_score": round(mean_val, 3),
            "water_coverage_pct": round(water_coverage_pct, 1),
            "overlay_base64": SpectralEngine._to_base64_png(rgb)
        }

    @staticmethod
    def compute_builtup_index(bands: np.ndarray) -> dict:
        """Built-up & impervious surface extraction proxy"""
        c, h, w = bands.shape
        if c >= 3:
            r = bands[0].astype(np.float32)
            g = bands[1].astype(np.float32)
            b = bands[2].astype(np.float32)
            # High brightness and low chromaticity indicate concrete/built structures
            intensity = (r + g + b) / 3.0
            saturation = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
            built = intensity / (saturation + 30.0)
        else:
            built = bands[0].astype(np.float32)

        p2, p98 = np.percentile(built, (5, 95))
        norm = np.clip((built - p2) / (p98 - p2 + 1e-6), 0, 1)

        rgb = SpectralEngine._colorize_palette(norm, 0.2, 0.85, "urban")
        builtup_pct = float(np.sum(norm > 0.55) / norm.size * 100)

        return {
            "index_name": "Built-up & Infrastructure Index",
            "builtup_coverage_pct": round(builtup_pct, 1),
            "overlay_base64": SpectralEngine._to_base64_png(rgb)
        }

    @staticmethod
    def _colorize_palette(arr: np.ndarray, vmin: float, vmax: float, theme: str) -> np.ndarray:
        norm = np.clip((arr - vmin) / (vmax - vmin + 1e-6), 0.0, 1.0)
        h, w = arr.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        if theme == "vegetation":
            # Red/Yellow/Green
            rgb[..., 0] = ((1.0 - norm) * 200 + 40).astype(np.uint8)
            rgb[..., 1] = (norm * 230 + 25).astype(np.uint8)
            rgb[..., 2] = 30
        elif theme == "water":
            # Sandy/Dark -> Deep Cyan/Blue
            rgb[..., 0] = ((1.0 - norm) * 150).astype(np.uint8)
            rgb[..., 1] = (norm * 180 + 40).astype(np.uint8)
            rgb[..., 2] = (norm * 255).astype(np.uint8)
        else: # urban
            # Blue-grey -> Gold/Orange/Red
            rgb[..., 0] = (norm * 240 + 15).astype(np.uint8)
            rgb[..., 1] = (norm * 140 + 20).astype(np.uint8)
            rgb[..., 2] = ((1.0 - norm) * 180).astype(np.uint8)

        return rgb

    @staticmethod
    def _to_base64_png(rgb_arr: np.ndarray) -> str:
        img = Image.fromarray(rgb_arr)
        if max(img.width, img.height) > 800:
            scale = 800.0 / max(img.width, img.height)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
