"""
ADTC 2026 Benchmark Runner
Runs the official performance tests required for the ADTC 2026 submission.

Usage:
    python scripts/run_benchmarks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.test_performance import run_all_benchmarks
from backend.utils.logger import get_logger

logger = get_logger("run_benchmarks")


def main():
    print("Running ADTC 2026 performance benchmarks …")
    results = run_all_benchmarks()
    print("\n✅ Benchmarks complete. Results saved to submission/performance_results.txt")


if __name__ == "__main__":
    main()
