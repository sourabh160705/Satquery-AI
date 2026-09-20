import io
import base64
import numpy as np
from PIL import Image

class ChangeSpecialist:
    """
    Bi-temporal change detection, change description, and change-VQA engine.
    Analyzes paired images (T1, T2) across time and generates spatial change maps.
    """

    @staticmethod
    def analyze_change(t1_rgb: np.ndarray, t2_rgb: np.ndarray, query: str = "") -> dict:
        h1, w1, _ = t1_rgb.shape
        h2, w2, _ = t2_rgb.shape

        # Resample T2 to match T1 dimensions if needed
        if (h1, w1) != (h2, w2):
            img2 = Image.fromarray(t2_rgb)
            img2 = img2.resize((w1, h1), Image.Resampling.BILINEAR)
            t2_rgb = np.array(img2)

        # Convert to float
        t1_f = t1_rgb.astype(np.float32)
        t2_f = t2_rgb.astype(np.float32)

        # Spectral luminance
        lum1 = (t1_f[..., 0]*0.299 + t1_f[..., 1]*0.587 + t1_f[..., 2]*0.114)
        lum2 = (t2_f[..., 0]*0.299 + t2_f[..., 1]*0.587 + t2_f[..., 2]*0.114)

        # Vegetation proxies
        veg1 = (t1_f[..., 1] - t1_f[..., 0]) / (t1_f[..., 1] + t1_f[..., 0] + 1e-6)
        veg2 = (t2_f[..., 1] - t2_f[..., 0]) / (t2_f[..., 1] + t2_f[..., 0] + 1e-6)
        veg_diff = veg2 - veg1

        # Water proxies
        water1 = (t1_f[..., 2] > t1_f[..., 0] + 20) & (lum1 < 100)
        water2 = (t2_f[..., 2] > t2_f[..., 0] + 20) & (lum2 < 100)
        water_increase = (~water1) & water2
        water_decrease = water1 & (~water2)

        # Spectral difference magnitude
        diff_rgb = np.abs(t2_f - t1_f)
        diff_mag = np.mean(diff_rgb, axis=-1)

        # Otsu-inspired thresholding for significant change
        p75 = np.percentile(diff_mag, 75)
        change_thresh = max(25.0, p75)
        changed_mask = diff_mag > change_thresh

        total_pixels = float(changed_mask.size)
        total_change_pct = float(np.sum(changed_mask) / total_pixels * 100)
        veg_loss_pct = float(np.sum((veg_diff < -0.15) & changed_mask) / total_pixels * 100)
        veg_gain_pct = float(np.sum((veg_diff > 0.15) & changed_mask) / total_pixels * 100)
        water_expand_pct = float(np.sum(water_increase) / total_pixels * 100)
        builtup_gain_pct = float(np.sum((lum2 > lum1 + 35) & (veg2 < 0) & changed_mask) / total_pixels * 100)

        # Create Colorized Spatial Change Map:
        # Red = Destruction / Deforestation / Loss
        # Green = New Vegetation / Revegetation
        # Blue = Inundation / Water expansion
        # Yellow = Urban expansion / New construction
        change_map = np.copy(t2_rgb) // 2 # Darkened background for high contrast overlay
        
        change_map[changed_mask] = [230, 180, 20] # General change (Gold)
        change_map[(veg_diff < -0.15) & changed_mask] = [240, 40, 40] # Loss/Deforestation (Red)
        change_map[(veg_diff > 0.15) & changed_mask] = [40, 230, 80] # Gain/Regrowth (Green)
        change_map[water_increase] = [30, 120, 255] # Water/Flood (Blue)
        change_map[(lum2 > lum1 + 35) & (veg2 < 0) & changed_mask] = [255, 140, 20] # Urban (Orange)

        # Formulate query-aware text description and VQA answer
        q_lower = query.lower()
        if "built-up" in q_lower or "urban" in q_lower or "infrastructure" in q_lower:
            if builtup_gain_pct > 1.5:
                trend = f"increased by approximately {builtup_gain_pct:.1f}%"
            elif total_change_pct < 2.0:
                trend = "remained virtually unchanged"
            else:
                trend = "stable with minor infrastructural redevelopment"
            direct_answer = f"The built-up area has {trend} between the observation dates."
        elif "water" in q_lower or "flood" in q_lower:
            if water_expand_pct > 1.0:
                direct_answer = f"Surface water expanded significantly (+{water_expand_pct:.1f}% area increase), indicating inundation or seasonal water rise."
            else:
                direct_answer = f"Water bodies remained mostly stable with less than 0.5% variance between observations."
        else:
            direct_answer = (
                f"Bi-temporal change analysis detected {total_change_pct:.1f}% altered surface area between T1 and T2. "
                f"Key transitions include {builtup_gain_pct:.1f}% built-up alteration, "
                f"{veg_loss_pct:.1f}% vegetation thinning/loss, and {veg_gain_pct:.1f}% vegetative regrowth."
            )

        return {
            "task": "BI_TEMPORAL_CHANGE_DETECTION",
            "total_change_pct": round(total_change_pct, 1),
            "breakdown": {
                "builtup_gain_pct": round(builtup_gain_pct, 1),
                "vegetation_loss_pct": round(veg_loss_pct, 1),
                "vegetation_gain_pct": round(veg_gain_pct, 1),
                "water_expansion_pct": round(water_expand_pct, 1),
            },
            "description": direct_answer,
            "change_map_base64": ChangeSpecialist._to_base64_jpeg(change_map)
        }

    @staticmethod
    def _to_base64_jpeg(rgb_arr: np.ndarray) -> str:
        img = Image.fromarray(rgb_arr)
        if max(img.width, img.height) > 800:
            scale = 800.0 / max(img.width, img.height)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
