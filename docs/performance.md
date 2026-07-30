# Performance verification

Run `venv\\Scripts\\python.exe scripts/test_performance.py` from the repository root. The script records system memory, local model loading, RAG retrieval, and inference timing in `submission/performance_results.txt`.

The benchmark reports whether the local model actually loaded. A stub result is not a passing model-performance result; it means the configured GGUF is absent or incompatible. RAG retrieval can still be measured independently from the LLM.

Targets from the project plan are: retrieval under 500 ms, short responses under 5 seconds, long responses under 15 seconds, idle memory under 4 GB, and active memory under 7 GB. Validate token speed and model load time on the deployment machine.
