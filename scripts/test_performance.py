"""
Performance Testing Script — ADTC 2026 Challenge requirement.
Tests model load time, memory usage, inference speed, and RAG latency.

Usage:
    python scripts/test_performance.py
"""

import sys
import time
import json
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.utils.logger import get_logger
from backend.utils.metrics import collect_system_metrics

logger = get_logger("test_performance")

TEST_QUERIES = [
    "What is malaria?",
    "What are the symptoms of typhoid fever?",
    "How do I treat dehydration in a child?",
    "What medications are used for hypertension?",
    "What are the signs of a stroke and what should I do?",
]


def test_model_load_time() -> dict:
    from backend.core.llm_engine import LLMEngine
    engine = LLMEngine()
    t0 = time.perf_counter()
    engine.load_model()
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "test": "Model Load Time",
        "result_ms": elapsed,
        "model_loaded": engine._model is not None,
        "stub_mode": engine._model is None,
    }


def test_inference_speed(engine=None) -> list:
    from backend.core.llm_engine import LLMEngine
    if engine is None:
        engine = LLMEngine()
        engine.load_model()

    results = []
    for query in TEST_QUERIES:
        mem_before = collect_system_metrics()
        t0 = time.perf_counter()
        response = engine.generate(query, max_tokens=256)
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        mem_after = collect_system_metrics()
        tokens_approx = len(response.split())
        results.append({
            "query": query[:50],
            "response_ms": elapsed,
            "response_tokens_approx": tokens_approx,
            "tokens_per_second": round(tokens_approx / (elapsed / 1000), 1) if elapsed > 0 else 0,
            "memory_delta_gb": round(mem_after["memory_used_gb"] - mem_before["memory_used_gb"], 3),
        })
        logger.info("Query: '%s' → %d ms, ~%d tokens", query[:40], elapsed, tokens_approx)

    return results


def test_rag_retrieval_latency() -> dict:
    from backend.core.rag_engine import rag_engine
    from backend.core.embedding_service import embedding_service
    embedding_service.load_model()
    rag_engine.set_embedder(embedding_service)
    rag_engine.initialize()

    t0 = time.perf_counter()
    _ = rag_engine.retrieve("malaria symptoms treatment")
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "test": "RAG Retrieval Latency",
        "result_ms": elapsed,
        "knowledge_base_docs": rag_engine.get_collection_count(),
    }


def test_memory_usage() -> dict:
    metrics = collect_system_metrics()
    return {"test": "System Memory", **metrics}


def run_all_benchmarks() -> dict:
    logger.info("=" * 60)
    logger.info("AfriHealth Assistant — Performance Benchmarks")
    logger.info("Target hardware: Intel i5 / Ryzen 5, 8GB RAM")
    logger.info("=" * 60)

    results = {
        "system":        test_memory_usage(),
        "model_load":    test_model_load_time(),
        "rag_retrieval": test_rag_retrieval_latency(),
        "inference":     test_inference_speed(),
    }

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"System RAM: {results['system']['memory_used_gb']} / {results['system']['memory_total_gb']} GB")
    print(f"Model load: {results['model_load']['result_ms']} ms  (stub={results['model_load']['stub_mode']})")
    print(f"RAG retrieval: {results['rag_retrieval']['result_ms']} ms")
    print("\nInference per query:")
    for r in results["inference"]:
        print(f"  [{r['response_ms']} ms | {r['tokens_per_second']} tok/s] {r['query']}")
    print("=" * 60)

    # Save to file
    out_path = Path("submission") / "performance_results.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to %s", out_path)

    return results


if __name__ == "__main__":
    run_all_benchmarks()
