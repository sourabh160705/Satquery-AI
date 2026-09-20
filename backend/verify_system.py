import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_data.loader import generate_sample_scenes, BENCHMARK_DIR
from engine.geotiff_parser import GeoTIFFParser
from agent.orchestrator import AgenticOrchestrator

def test_full_pipeline():
    print("=== 1. Generating & Verifying Benchmark Scenes ===")
    generate_sample_scenes()
    optical_file = os.path.join(BENCHMARK_DIR, "sample_sentinel2_optical.tif")
    t1_file = os.path.join(BENCHMARK_DIR, "bitemporal_t1_pre.tif")
    t2_file = os.path.join(BENCHMARK_DIR, "bitemporal_t2_post.tif")
    sar_file = os.path.join(BENCHMARK_DIR, "pair_risat_sar.tif")

    assert os.path.exists(optical_file), "Optical sample missing"
    assert os.path.exists(t1_file) and os.path.exists(t2_file), "Bitemporal samples missing"
    assert os.path.exists(sar_file), "SAR sample missing"
    print("[OK] All 3 benchmark datasets verified.")

    print("\n=== 2. Testing GeoTIFF Parsing ===")
    with open(optical_file, "rb") as f:
        opt_parsed = GeoTIFFParser.read_image_bytes(f.read(), filename="sample_sentinel2_optical.tif")
    assert opt_parsed["metadata"]["bands"] >= 3, "Invalid band count"
    assert opt_parsed["preview_base64"].startswith("data:image/jpeg;base64,"), "Preview generation failed"
    print(f"[OK] Parsed: {opt_parsed['metadata']['format']} {opt_parsed['metadata']['width']}x{opt_parsed['metadata']['height']} | Modality: {opt_parsed['metadata']['modality']}")

    print("\n=== 3. Testing Single-Image Baseline: Captioning ===")
    cap_res = AgenticOrchestrator.process_query(
        query="Describe the land-cover and major objects visible in this image.",
        images_data=[opt_parsed]
    )
    assert cap_res["task"] == "SCENE_CAPTIONING", f"Wrong task: {cap_res['task']}"
    assert "terrain" in cap_res["result"]["text_answer"].lower(), "Empty caption"
    print(f"[OK] Task: {cap_res['task']} | Confidence: {cap_res['auditable_trace']['estimated_confidence']}")
    print(f"  Result: {cap_res['result']['text_answer'][:120]}...")

    print("\n=== 4. Testing Single-Image Baseline: Text-Guided Grounding ===")
    grd_res = AgenticOrchestrator.process_query(
        query="Highlight the water body referred to in the query.",
        images_data=[opt_parsed]
    )
    assert grd_res["task"] == "TEXT_GUIDED_GROUNDING", f"Wrong task: {grd_res['task']}"
    assert len(grd_res["result"]["bounding_boxes"]) > 0, "No bounding box found"
    print(f"[OK] Task: {grd_res['task']} | Grounded: {grd_res['result']['target_class']} | Boxes: {len(grd_res['result']['bounding_boxes'])}")

    print("\n=== 5. Testing Single-Image Baseline: RS-VQA ===")
    vqa_res = AgenticOrchestrator.process_query(
        query="Is there an urban settlement or building cluster present?",
        images_data=[opt_parsed]
    )
    assert vqa_res["task"] == "SINGLE_IMAGE_VQA", f"Wrong task: {vqa_res['task']}"
    print(f"[OK] Task: {vqa_res['task']} | Answer: {vqa_res['result']['text_answer']}")

    print("\n=== 6. Testing Bi-Temporal Change Detection ===")
    with open(t1_file, "rb") as f1, open(t2_file, "rb") as f2:
        t1_parsed = GeoTIFFParser.read_image_bytes(f1.read(), filename="bitemporal_t1_pre.tif")
        t2_parsed = GeoTIFFParser.read_image_bytes(f2.read(), filename="bitemporal_t2_post.tif")
    
    cd_res = AgenticOrchestrator.process_query(
        query="What changed between these two dates, and where did the change occur?",
        images_data=[t1_parsed, t2_parsed]
    )
    assert cd_res["task"] == "BI_TEMPORAL_CHANGE", f"Wrong task: {cd_res['task']}"
    assert cd_res["result"]["quantitative_change_pct"] > 0, "Change percent is 0"
    assert cd_res["visual_evidence_base64"] is not None, "Change map missing"
    print(f"[OK] Task: {cd_res['task']} | Total Change: {cd_res['result']['quantitative_change_pct']}%")
    print(f"  Summary: {cd_res['result']['text_answer']}")

    print("\n=== 7. Testing Cross-Modal Optical + SAR Analysis ===")
    with open(sar_file, "rb") as fs:
        sar_parsed = GeoTIFFParser.read_image_bytes(fs.read(), filename="pair_risat_sar.tif")
    
    sar_res = AgenticOrchestrator.process_query(
        query="Use the optical and SAR images together to identify built-up and water-covered regions.",
        images_data=[opt_parsed, sar_parsed]
    )
    assert sar_res["task"] == "CROSS_MODAL_OPTICAL_SAR", f"Wrong task: {sar_res['task']}"
    assert "confirmed_builtup_coverage_pct" in sar_res["result"]["cross_modal_metrics"], "Metrics missing"
    print(f"[OK] Task: {sar_res['task']} | Urban: {sar_res['result']['cross_modal_metrics']['confirmed_builtup_coverage_pct']}% | Water: {sar_res['result']['cross_modal_metrics']['confirmed_water_coverage_pct']}%")

    print("\n=== 8. Validating Auditable Execution Trace ===")
    trace = sar_res["auditable_trace"]
    assert trace["execution_status"] == "SUCCESS", "Execution not SUCCESS"
    assert len(trace["models_or_tools_invoked"]) > 0, "No tools recorded in trace"
    assert trace["latency_ms"] > 0, "Latency not measured"
    print("[OK] Auditable Trace Validated:")
    for k, v in trace.items():
        print(f"  - {k}: {v}")

    print("\n[SUCCESS] ALL TESTS PASSED! Remote Sensing Agentic Backend is fully operational.")

if __name__ == "__main__":
    test_full_pipeline()
