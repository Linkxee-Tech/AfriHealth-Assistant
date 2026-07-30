"""General helper functions."""

import time
import uuid
from datetime import datetime, date
import re


def generate_session_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp(value) -> str:
    """Return a consistent, human-readable timestamp for API/UI output."""
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return ""


def sanitize_input(value: str, max_length: int = 4096) -> str:
    """Trim control characters and bound user text before it reaches prompts."""
    if value is None:
        return ""
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", str(value))
    return " ".join(value.strip().split())[:max_length]


def generate_mrn(sequence: int = 1, year: int = None) -> str:
    return f"AH-{year or datetime.now().year}-{int(sequence):05d}"


def timer():
    """Simple wall-clock timer. Returns elapsed_ms callable."""
    start = time.perf_counter()
    return lambda: round((time.perf_counter() - start) * 1000, 2)
