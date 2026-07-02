"""
Prepare Submission Script
Verifies the project is ready for ADTC 2026 submission and packages it.

Usage:
    python scripts/prepare_submission.py --gate 1    # Gate 1 (24 July)
    python scripts/prepare_submission.py --final     # Final (27 Aug)
"""

import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.utils.logger import get_logger

logger = get_logger("prepare_submission")

ROOT = Path(__file__).resolve().parent.parent
SUBMISSION_DIR = ROOT / "submission"


def check_requirements() -> list:
    issues = []
    checks = [
        (ROOT / "README.md",            "README.md missing"),
        (ROOT / "requirements.txt",     "requirements.txt missing"),
        (ROOT / "frontend" / "app.py",  "frontend/app.py missing"),
        (ROOT / "backend"  / "main.py", "backend/main.py missing"),
        (ROOT / "LICENSE",              "LICENSE missing"),
    ]
    for path, msg in checks:
        if not path.exists():
            issues.append(msg)
    return issues


def run_tests() -> bool:
    logger.info("Running backend tests …")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/", "-v", "--tb=short"],
        cwd=str(ROOT), capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode == 0


def run_frontend_tests() -> bool:
    logger.info("Running frontend tests …")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "frontend/tests/", "-v", "--tb=short"],
        cwd=str(ROOT), capture_output=True, text=True
    )
    print(result.stdout)
    return result.returncode == 0


def create_zip(gate: str) -> str:
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M")
    zip_name    = f"AfriHealth-Assistant_{gate}_{timestamp}"
    zip_path    = SUBMISSION_DIR / gate / zip_name

    exclude_dirs = {
        "__pycache__", ".pytest_cache", ".git", "afrihealth.db",
        "backend/models/llm", "backend/data/vector_db",
    }

    shutil.make_archive(
        str(zip_path), "zip", str(ROOT),
        logger=logger,
    )
    return str(zip_path) + ".zip"


def write_github_link_placeholder(gate_dir: Path):
    (gate_dir / "GitHub_Repo_Link.txt").write_text(
        "GitHub Repository: https://github.com/YOUR_USERNAME/AfriHealth-Assistant\n"
        "Please update this link before submission.\n"
    )


def prepare(gate: str = "Gate_1_Submission"):
    logger.info("Preparing %s …", gate)
    gate_dir = SUBMISSION_DIR / gate
    gate_dir.mkdir(parents=True, exist_ok=True)

    # 1. Check requirements
    issues = check_requirements()
    if issues:
        for issue in issues:
            logger.error("❌ %s", issue)
        logger.error("Fix the above issues before submitting.")
        return

    # 2. Run tests
    backend_ok  = run_tests()
    frontend_ok = run_frontend_tests()

    if not backend_ok or not frontend_ok:
        logger.warning("⚠️  Some tests failed. Review before submitting.")

    # 3. GitHub link placeholder
    write_github_link_placeholder(gate_dir)

    # 4. Create zip
    zip_path = create_zip(gate)

    print("\n" + "=" * 60)
    print(f"✅ Submission prepared: {gate}")
    print(f"   Backend tests:  {'PASS' if backend_ok else 'FAIL'}")
    print(f"   Frontend tests: {'PASS' if frontend_ok else 'FAIL'}")
    print(f"   Package: {zip_path}")
    print(f"   Update GitHub_Repo_Link.txt before submitting!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate",  default="Gate_1_Submission")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    gate = "Final_Submission" if args.final else args.gate
    prepare(gate)
