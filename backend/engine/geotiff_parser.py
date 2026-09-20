import io
import base64
import numpy as np
from PIL import Image
import tifffile

class GeoTIFFParser:
    """
    Parses Geospatial TIFF, standard TIFF, PNG, and JPEG imagery.
    Extracts bands, statistics, metadata, and generates normalized RGB previews.
    """

    @staticmethod
    def read_image_bytes(file_bytes: bytes, filename: str = "image.tif") -> dict:
        is_tiff = filename.lower().endswith(('.tif', '.tiff'))
        metadata = {
            "filename": filename,
            "format": "TIFF/GeoTIFF" if is_tiff else filename.split('.')[-1].upper(),
            "width": 0,
            "height": 0,
            "bands": 0,
            "dtype": "unknown",
            "modality": "unknown",
            "geo_tags": {}
        }

        bands_data = None

        if is_tiff:
            try:
                with tifffile.TiffFile(io.BytesIO(file_bytes)) as tif:
                    arr = tif.asarray()
                    if arr.ndim == 2:
                        bands_data = arr[np.newaxis, :, :]
                    elif arr.ndim == 3:
                        if arr.shape[0] <= 16 and arr.shape[0] < arr.shape[1]:
                            bands_data = arr
                        elif arr.shape[2] <= 16:
                            bands_data = np.transpose(arr, (2, 0, 1))
                        else:
                            bands_data = arr[np.newaxis, :, :]
                    
                    metadata["height"] = bands_data.shape[1]
                    metadata["width"] = bands_data.shape[2]
                    metadata["bands"] = bands_data.shape[0]
                    metadata["dtype"] = str(arr.dtype)

                    # Inspect TIFF tags
                    if len(tif.pages) > 0:
                        page = tif.pages[0]
                        for tag in page.tags:
                            if tag.name in ("ModelPixelScaleTag", "ModelTiepointTag", "GeoKeyDirectoryTag", "ImageDescription"):
                                metadata["geo_tags"][tag.name] = str(tag.value)[:100]
            except Exception as e:
                # Fallback to PIL
                img = Image.open(io.BytesIO(file_bytes))
                arr = np.array(img)
                if arr.ndim == 2:
                    bands_data = arr[np.newaxis, :, :]
                else:
                    bands_data = np.transpose(arr, (2, 0, 1))
                metadata["height"] = img.height
                metadata["width"] = img.width
                metadata["bands"] = bands_data.shape[0]
                metadata["dtype"] = str(arr.dtype)
        else:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            arr = np.array(img)
            bands_data = np.transpose(arr, (2, 0, 1))
            metadata["height"] = img.height
            metadata["width"] = img.width
            metadata["bands"] = 3
            metadata["dtype"] = str(arr.dtype)

        # Infer modality (Optical vs SAR vs Multispectral)
        fn_lower = filename.lower()
        if "sar" in fn_lower or "risat" in fn_lower or "sentinel1" in fn_lower or "s1" in fn_lower:
            metadata["modality"] = "SAR"
        elif metadata["bands"] == 1:
            # Single channel might be panchromatic or SAR
            metadata["modality"] = "SAR / Single-band"
        elif metadata["bands"] == 3:
            metadata["modality"] = "Optical RGB"
        elif metadata["bands"] > 3:
            metadata["modality"] = "Multispectral"
        else:
            metadata["modality"] = "Optical"

        # Generate normalized visual RGB representation (2% - 98% percentile stretch)
        visual_rgb = GeoTIFFParser._normalize_to_rgb(bands_data, metadata["modality"])
        preview_base64 = GeoTIFFParser._to_base64_jpeg(visual_rgb)

        return {
            "metadata": metadata,
            "raw_bands": bands_data,
            "visual_rgb": visual_rgb,
            "preview_base64": preview_base64
        }

    @staticmethod
    def _normalize_to_rgb(bands_data: np.ndarray, modality: str) -> np.ndarray:
        c, h, w = bands_data.shape
        if c == 1:
            band = bands_data[0].astype(np.float32)
            # Log transform for SAR speckle if dynamic range is large
            if modality.startswith("SAR"):
                band = np.log1p(np.maximum(band, 0))
            p2, p98 = np.percentile(band, (2, 98))
            if p98 > p2:
                norm = np.clip((band - p2) / (p98 - p2), 0, 1) * 255.0
            else:
                norm = np.zeros_like(band)
            rgb = np.stack([norm, norm, norm], axis=-1).astype(np.uint8)
            return rgb
        elif c >= 3:
            # Take first 3 channels as R, G, B
            rgb_layers = []
            for i in range(3):
                b = bands_data[i].astype(np.float32)
                p2, p98 = np.percentile(b, (2, 98))
                if p98 > p2:
                    norm = np.clip((b - p2) / (p98 - p2), 0, 1) * 255.0
                else:
                    norm = np.zeros_like(b)
                rgb_layers.append(norm)
            return np.stack(rgb_layers, axis=-1).astype(np.uint8)
        else:
            # 2 bands - create pseudo color
            b1 = GeoTIFFParser._normalize_band(bands_data[0])
            b2 = GeoTIFFParser._normalize_band(bands_data[1])
            avg = ((b1.astype(np.float32) + b2.astype(np.float32)) / 2).astype(np.uint8)
            return np.stack([b1, avg, b2], axis=-1)

    @staticmethod
    def _normalize_band(b: np.ndarray) -> np.ndarray:
        b_f = b.astype(np.float32)
        p2, p98 = np.percentile(b_f, (2, 98))
        if p98 > p2:
            return (np.clip((b_f - p2) / (p98 - p2), 0, 1) * 255.0).astype(np.uint8)
        return np.zeros_like(b, dtype=np.uint8)

    @staticmethod
    def _to_base64_jpeg(rgb_arr: np.ndarray) -> str:
        # Resize if very large for fast web transfer
        h, w, _ = rgb_arr.shape
        max_dim = 1024
        img = Image.fromarray(rgb_arr)
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
