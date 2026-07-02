"""Input validation utilities."""

from fastapi import HTTPException


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
