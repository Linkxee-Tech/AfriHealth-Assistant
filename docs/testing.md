# Testing Guide

## Backend Tests
```bash
pytest backend/tests/ -v
# 26 tests: test_api (16), test_llm_engine (5), test_rag_engine (5)
```

## Frontend Tests
```bash
cd frontend && pytest tests/test_components.py -v
# 11 tests covering all 9 pages and key interactions
```

## Running Both
```bash
pytest backend/tests/ frontend/tests/ -v
```
