"""Performance metrics collection."""

import time
import psutil
from dataclasses import dataclass, field
from typing import Optional


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
