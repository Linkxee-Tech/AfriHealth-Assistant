"""General helper functions."""

import time
import uuid
from datetime import datetime


def generate_session_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timer():
    """Simple wall-clock timer. Returns elapsed_ms callable."""
    start = time.perf_counter()
    return lambda: round((time.perf_counter() - start) * 1000, 2)
