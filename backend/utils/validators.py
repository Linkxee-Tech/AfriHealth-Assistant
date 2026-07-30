"""Input validation utilities."""

from fastapi import HTTPException
from pathlib import Path
from typing import Iterable, Mapping


def validate_query(query: str) -> str:
    query = query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be empty.")
    if len(query) > 4096:
        raise HTTPException(status_code=422, detail="Query exceeds maximum length of 4096 characters.")
    return query


def validate_metric_value(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Metric value cannot be empty.")
    return value


def validate_symptoms(symptoms: Iterable[str]) -> list[str]:
    values = [str(item).strip() for item in (symptoms or []) if str(item).strip()]
    if not values or any(len(item) > 200 for item in values):
        raise HTTPException(status_code=422, detail="Provide one or more valid symptoms.")
    return values


def validate_metrics(metrics: Mapping) -> Mapping:
    if not isinstance(metrics, Mapping) or not metrics:
        raise HTTPException(status_code=422, detail="At least one metric is required.")
    return metrics


def validate_file(filename: str, size_bytes: int, max_size_bytes: int = 10 * 1024 * 1024) -> str:
    allowed = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"}
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix or 'none'}")
    if size_bytes > max_size_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")
    return suffix


def validate_patient(patient: Mapping) -> Mapping:
    if not patient.get("first_name") or not patient.get("last_name"):
        raise HTTPException(status_code=422, detail="First and last name are required.")
    return patient


def validate_drug(drug: str) -> str:
    value = str(drug or "").strip()
    if not value or len(value) > 100:
        raise HTTPException(status_code=422, detail="A valid drug name is required.")
    return value
