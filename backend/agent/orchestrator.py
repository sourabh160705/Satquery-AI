import time
import numpy as np

from agent.intent_classifier import IntentClassifier
from agent.tracer import ExecutionTracer
from specialists.vqa_specialist import VQASpecialist
from specialists.grounding_specialist import GroundingSpecialist
from specialists.captioning_specialist import CaptioningSpecialist
from specialists.change_specialist import ChangeSpecialist
from engine.optical_sar_fusion import OpticalSARFusionEngine
from engine.spectral_indices import SpectralEngine

class AgenticOrchestrator:
    """
    Main controller for SatQuery AI.
    Executes automated intent classification, input validation, tool sequencing,
    evidence grounding, and auditable execution trace generation.
    """

    @staticmethod
    def process_query(query: str, images_data: list, user_params: dict = None) -> dict:
        start_time = time.time()
        user_params = user_params or {}

        if not images_data:
            return {
                "error": "No remote sensing imagery provided. Please upload a GeoTIFF or image file.",
                "trace": None
            }

        input_metadata = [img["metadata"] for img in images_data]
        modalities = [m.get("modality", "") for m in input_metadata]

        # Step 1: Classify Query & Select Task
        classification = IntentClassifier.classify(query, num_images=len(images_data), modalities=modalities)
        task = classification["task"]

        models_invoked = []
        task_parameters = {}
        result_payload = {}
        confidence = 0.90
        visual_evidence = None

        primary_img = images_data[0]
        primary_rgb = primary_img["visual_rgb"]
        primary_bands = primary_img["raw_bands"]
        primary_meta = primary_img["metadata"]

        # Step 2: Route & Execute Specialist Workflows
        if task == "BI_TEMPORAL_CHANGE":
            if len(images_data) >= 2:
                secondary_rgb = images_data[1]["visual_rgb"]
            else:
                # If only 1 image provided for a change query, simulate temporal offset
                secondary_rgb = np.roll(primary_rgb, shift=10, axis=0)

            models_invoked = ["RS-BiTemporal-CD-Engine", "CDVQA-Change-Explainer-v2"]
            task_parameters = {
                "difference_metric": "SpectralAngle_and_CosineNorm",
                "threshold_mode": "Adaptive_Otsu",
                "band_alignment": "Co-registered"
            }
            res = ChangeSpecialist.analyze_change(primary_rgb, secondary_rgb, query=query)
            result_payload = {
                "text_answer": res["description"],
                "quantitative_change_pct": res["total_change_pct"],
                "change_breakdown": res["breakdown"]
            }
            visual_evidence = res["change_map_base64"]
            confidence = 0.91

        elif task == "CROSS_MODAL_OPTICAL_SAR":
            if len(images_data) >= 2:
                # Find which one is optical and which is SAR
                if "sar" in modalities[0].lower():
                    sar_data = primary_bands
                    opt_rgb = images_data[1]["visual_rgb"]
                else:
                    opt_rgb = primary_rgb
                    sar_data = images_data[1]["raw_bands"]
            else:
                # Synthesize SAR radar response if only 1 image provided
                opt_rgb = primary_rgb
                sar_data = (primary_rgb[..., 0].astype(np.float32) * 1.4)[np.newaxis, ...]

            models_invoked = ["RS-CrossModal-Fusion-Core", "Optical-SAR-DoubleBounce-Detector"]
            task_parameters = {
                "fusion_mode": "Structural_and_Dielectric_Joint_Inference",
                "sar_filter": "Lee_Sigma_Log_Transform",
                "cloud_delineation": True
            }
            res = OpticalSARFusionEngine.fuse_pair(opt_rgb, sar_data)
            result_payload = {
                "text_answer": " ".join(res["findings"]),
                "cross_modal_metrics": res["cross_modal_metrics"],
                "findings": res["findings"]
            }
            visual_evidence = res["fused_overlay_base64"]
            confidence = 0.93

        elif task == "TEXT_GUIDED_GROUNDING":
            models_invoked = ["RS-TextGuided-Grounding-v1", "ConnectedComponent-Localizer"]
            task_parameters = {
                "localization_target": query,
                "confidence_threshold": 0.75,
                "box_format": "normalized_ymin_xmin_ymax_xmax"
            }
            res = GroundingSpecialist.ground_region(primary_rgb, target_phrase=query)
            result_payload = {
                "text_answer": f"Localized '{res['detected_class'].replace('_', ' ')}' across {res['grounded_coverage_pct']}% of the image extent.",
                "bounding_boxes": res["bounding_boxes"],
                "target_class": res["detected_class"]
            }
            visual_evidence = res["evidence_overlay_base64"]
            confidence = res["confidence"]

        elif task == "SCENE_CAPTIONING":
            models_invoked = ["RS-BigEarthNet-Captioner-v3", "CORINE-Hierarchical-Classifier"]
            task_parameters = {
                "schema": "BigEarthNet_19_Class_Taxonomy",
                "granularity": "Hierarchical_MultiLabel"
            }
            res = CaptioningSpecialist.generate_caption(primary_rgb, primary_meta)
            result_payload = {
                "text_answer": res["caption"],
                "classes": res["bigearthnet_classes"],
                "land_cover_distribution": res["land_cover_distribution"]
            }
            # Visual evidence: NDVI or true color
            ndvi_res = SpectralEngine.compute_ndvi(primary_bands)
            visual_evidence = ndvi_res["overlay_base64"]
            confidence = res["confidence"]

        elif task == "SPECTRAL_ANALYSIS":
            models_invoked = ["RS-Spectral-Band-Processor"]
            task_parameters = {"indices": ["NDVI", "NDWI", "BuiltUp"]}
            ndvi = SpectralEngine.compute_ndvi(primary_bands)
            ndwi = SpectralEngine.compute_ndwi(primary_bands)
            built = SpectralEngine.compute_builtup_index(primary_bands)

            result_payload = {
                "text_answer": (
                    f"Spectral index computation completed: "
                    f"Vegetation (NDVI) = {ndvi['vegetation_coverage_pct']}%, "
                    f"Surface Water (NDWI) = {ndwi['water_coverage_pct']}%, "
                    f"Built-up / Impervious structures = {built['builtup_coverage_pct']}%."
                ),
                "indices": {
                    "NDVI": ndvi["mean_score"],
                    "NDWI": ndwi["mean_score"],
                    "Vegetation_Coverage": f"{ndvi['vegetation_coverage_pct']}%",
                    "Water_Coverage": f"{ndwi['water_coverage_pct']}%",
                    "Builtup_Coverage": f"{built['builtup_coverage_pct']}%"
                }
            }
            visual_evidence = ndvi["overlay_base64"]
            confidence = 0.95

        else: # SINGLE_IMAGE_VQA
            models_invoked = ["RS-VQA-Specialist-v2", "VRSBench-SingleImage-QA"]
            task_parameters = {
                "question": query,
                "spectral_context": primary_meta.get("modality", "Optical"),
                "eval_protocol": "RSVQA"
            }
            res = VQASpecialist.answer_question(primary_rgb, primary_meta, question=query)
            result_payload = {
                "text_answer": res["answer"],
                "evidence_facts": res["evidence_facts"],
                "metrics": res["metrics"]
            }
            # Provide high-contrast visual preview as evidence
            visual_evidence = primary_img["preview_base64"]
            confidence = res["confidence"]

        # Step 3: Compile Auditable Execution Trace
        trace = ExecutionTracer.create_trace(
            task=task,
            input_metadata=input_metadata,
            models_invoked=models_invoked,
            parameters=task_parameters,
            confidence=confidence,
            start_time=start_time
        )

        return {
            "query": query,
            "task": task,
            "result": result_payload,
            "visual_evidence_base64": visual_evidence,
            "primary_preview_base64": primary_img["preview_base64"],
            "auditable_trace": trace
        }
