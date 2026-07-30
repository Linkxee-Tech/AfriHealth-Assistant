"""Repository-side verification for the professional 328-item checklist.

This checks wiring that can be proven from the repository. External credentials,
clinical sign-off, and the deferred GGUF are reported separately rather than
being silently treated as complete.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checklist", type=Path, help="Supplied checklist text file")
    parser.add_argument("--require-model", action="store_true", help="Fail if the configured GGUF is not present")
    args = parser.parse_args()

    checks: dict[str, bool] = {}
    if args.checklist and args.checklist.exists():
        checklist = args.checklist.read_text(encoding="utf-8", errors="replace")
        ids = re.findall(r"\b(?:P|F|B|I|K|H|G|O|T|D|DEP|CP)\d+\b", checklist)
        # The supplied document declares 328 but enumerates 524 unique IDs
        # (P23+F213+B90+I47+K19+H27+G21+O22+T21+D10+DEP16+CP15).
        # Report both values so the inconsistency cannot be hidden.
        checks["checklist_declared_total_328"] = "**328**" in checklist
        checks["checklist_ids_enumerated"] = len(set(ids)) == 524
    else:
        checks["checklist_file_supplied"] = False

    required_files = [
        "backend/main.py", "backend/config.py", "backend/api/routes/auth.py",
        "backend/api/routes/clinical.py", "backend/database/models.py",
        "backend/database/migrations/versions/0001_initial_schema.py",
        "frontend/app.py", "frontend/pages/6_🩺_Clinical_Support.py",
        "frontend/components/clinical_support.py", "frontend/components/gemini_integration.py",
        "docs/clinical_guide.md", "docs/hybrid_mode.md", "docs/performance.md",
    ]
    checks["required_repository_files"] = all((ROOT / path).exists() for path in required_files)

    auth = text("backend/api/routes/auth.py")
    model = text("backend/database/models.py")
    checks["password_recovery_routes"] = all(route in auth for route in ("/forgot-password", "/reset-password", "/admin-recover"))
    checks["password_recovery_storage"] = "class PasswordReset" in model and "password_resets" in model

    route_text = "\n".join(text(str(path.relative_to(ROOT))) for path in (ROOT / "backend/api/routes").glob("*.py"))
    expected_routes = ["/health", "/status", "/chat", "/metrics", "/documents", "/patients", "/clinical", "/online"]
    checks["core_route_groups"] = all(route in route_text for route in expected_routes)

    model_path = None
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines() if (ROOT / ".env").exists() else []:
        if line.startswith("MODEL_PATH="):
            model_path = line.split("=", 1)[1].strip()
    model_path = model_path or "backend/models/llm/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    resolved_model = Path(model_path)
    if not resolved_model.is_absolute():
        resolved_model = ROOT / resolved_model
    checks["gguf_path_wired"] = "Llama-3.2-3B-Instruct-Q4_K_M.gguf" in model_path
    checks["gguf_file_present"] = resolved_model.exists()

    result = {"checks": checks, "passed": sum(checks.values()), "total": len(checks), "model_path": model_path}
    print(json.dumps(result, indent=2))
    failed_required = [name for name, value in checks.items() if not value and name not in {"gguf_file_present", "checklist_file_supplied"}]
    if args.require_model and not checks["gguf_file_present"]:
        failed_required.append("gguf_file_present")
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
