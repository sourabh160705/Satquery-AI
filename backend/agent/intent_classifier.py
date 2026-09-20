import re

class IntentClassifier:
    """
    Classifies user queries into specific remote sensing specialist workflows
    and determines mandatory input configurations.
    """

    TASKS = {
        "BI_TEMPORAL_CHANGE": {
            "keywords": ["changed", "change", "difference", "between", "dates", "before", "after", "temporal", "increase", "decrease"],
            "requires_pair": True,
            "modality_requirement": "multitemporal"
        },
        "CROSS_MODAL_OPTICAL_SAR": {
            "keywords": ["sar", "radar", "optical and sar", "together", "cross-modal", "fusion", "cloud cover", "penetrate", "structural"],
            "requires_pair": True,
            "modality_requirement": "optical_sar"
        },
        "TEXT_GUIDED_GROUNDING": {
            "keywords": ["highlight", "locate", "where is", "find the", "bounding box", "pinpoint", "mark", "ground"],
            "requires_pair": False,
            "modality_requirement": "any"
        },
        "SCENE_CAPTIONING": {
            "keywords": ["describe", "caption", "summary", "overview", "what does this show", "scene description"],
            "requires_pair": False,
            "modality_requirement": "any"
        },
        "SPECTRAL_ANALYSIS": {
            "keywords": ["ndvi", "ndwi", "vegetation index", "water index", "builtup index", "spectral"],
            "requires_pair": False,
            "modality_requirement": "optical"
        },
        "SINGLE_IMAGE_VQA": {
            "keywords": ["is there", "how many", "what is", "are there", "does this", "can you see"],
            "requires_pair": False,
            "modality_requirement": "any"
        }
    }

    @staticmethod
    def classify(query: str, num_images: int = 1, modalities: list = None) -> dict:
        q_clean = query.lower().strip()
        modalities = modalities or []

        # 1. Check for explicit cross-modal keywords or if one is SAR and one is Optical
        has_sar = any("sar" in m.lower() for m in modalities)
        has_optical = any("optical" in m.lower() or "rgb" in m.lower() for m in modalities)

        if (has_sar and has_optical) or ("sar" in q_clean and "optical" in q_clean):
            return {
                "task": "CROSS_MODAL_OPTICAL_SAR",
                "confidence": 0.95,
                "reasoning": "Detected Optical + SAR paired input requirement from query keywords or ingested modalities."
            }

        # 2. Check for bi-temporal change queries
        if any(w in q_clean for w in IntentClassifier.TASKS["BI_TEMPORAL_CHANGE"]["keywords"]) and num_images >= 2:
            return {
                "task": "BI_TEMPORAL_CHANGE",
                "confidence": 0.94,
                "reasoning": "Detected multitemporal change comparison query on paired image inputs."
            }

        # 3. Grounding queries
        if any(w in q_clean for w in IntentClassifier.TASKS["TEXT_GUIDED_GROUNDING"]["keywords"]):
            return {
                "task": "TEXT_GUIDED_GROUNDING",
                "confidence": 0.92,
                "reasoning": "Detected text-guided localization / region highlighting intent."
            }

        # 4. Captioning queries
        if any(w in q_clean for w in IntentClassifier.TASKS["SCENE_CAPTIONING"]["keywords"]):
            return {
                "task": "SCENE_CAPTIONING",
                "confidence": 0.91,
                "reasoning": "Detected holistic scene captioning and land-cover description intent."
            }

        # 5. Spectral indices
        if any(w in q_clean for w in IntentClassifier.TASKS["SPECTRAL_ANALYSIS"]["keywords"]):
            return {
                "task": "SPECTRAL_ANALYSIS",
                "confidence": 0.93,
                "reasoning": "Detected spectral index computation intent (NDVI/NDWI/NDBI)."
            }

        # 6. Default to Single-Image VQA
        return {
            "task": "SINGLE_IMAGE_VQA",
            "confidence": 0.88,
            "reasoning": "Classified as general Remote Sensing Visual Question Answering (RS-VQA)."
        }
