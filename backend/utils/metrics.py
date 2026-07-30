"""Performance metrics collection."""

import time
import psutil
from dataclasses import dataclass, field
from typing import Optional

_history = []
_api_cost_usd = 0.0


@dataclass
class InferenceMetrics:
    query_length: int = 0
    response_length: int = 0
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    total_ms: float = 0.0
    tokens_per_second: float = 0.0
    memory_used_gb: float = 0.0


def collect_system_metrics() -> dict:
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    return {
        "cpu_percent": cpu,
        "memory_used_gb": round(mem.used / 1024 ** 3, 2),
        "memory_total_gb": round(mem.total / 1024 ** 3, 2),
        "memory_percent": mem.percent,
    }


def track_memory() -> dict:
    return collect_system_metrics()


def track_inference_time(elapsed_ms: float, query_length: int = 0, response_length: int = 0) -> dict:
    item = {"elapsed_ms": float(elapsed_ms), "query_length": query_length, "response_length": response_length}
    _history.append(item)
    del _history[:-1000]
    return item


def track_api_cost(cost_usd: float, tokens_used: int = 0) -> dict:
    global _api_cost_usd
    _api_cost_usd += max(0.0, float(cost_usd))
    return {"estimated_cost_usd": round(_api_cost_usd, 6), "tokens_used": int(tokens_used)}


def get_performance_stats() -> dict:
    values = [item["elapsed_ms"] for item in _history]
    return {"requests": len(values), "average_ms": round(sum(values) / len(values), 2) if values else 0.0,
            "last_ms": values[-1] if values else 0.0, **collect_system_metrics()}
