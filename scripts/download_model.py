"""
Download the local LLM model for AfriHealth Assistant.
Downloads Phi-3 Mini 4K Instruct (Q4_K_M GGUF) from Hugging Face.
This model is ~2.2 GB and runs well on machines with 8 GB RAM.
"""

import os
import sys
import time
import urllib.request
from pathlib import Path

# -----------------------------------------------------------------------
# Model configuration
# -----------------------------------------------------------------------
MODEL_NAME = "phi-3-mini-q4.gguf"
MODEL_SIZE_GB = 2.2
MODEL_URL = (
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf"
    "/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    "?download=true"
)
DEST_DIR  = Path(__file__).resolve().parent.parent / "backend" / "models" / "llm"
DEST_PATH = DEST_DIR / MODEL_NAME

# -----------------------------------------------------------------------

def human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


def download_with_resume(url: str, dest: Path, chunk_size: int = 1024 * 1024) -> bool:
    """Download a file with HTTP Range resume support."""
    import urllib.request as req

    tmp = dest.with_suffix(".tmp")
    existing = tmp.stat().st_size if tmp.exists() else 0

    headers = {}
    if existing:
        headers["Range"] = f"bytes={existing}-"
        print(f"  Resuming from {human_size(existing)} already downloaded...")

    request = req.Request(url, headers=headers)
    try:
        response = req.urlopen(request, timeout=60)
    except Exception as exc:
        print(f"  Connection error: {exc}")
        return False

    total = int(response.headers.get("Content-Length", 0)) + existing
    downloaded = existing

    t0 = time.time()
    mode = "ab" if existing else "wb"
    with open(tmp, mode) as f:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = min(downloaded / total * 100, 100)
                bar = "#" * int(pct // 2)
                elapsed = time.time() - t0
                speed = (downloaded - existing) / max(elapsed, 1)
                remain = (total - downloaded) / max(speed, 1)
                print(
                    f"\r  [{bar:<50}] {pct:5.1f}%  "
                    f"{human_size(downloaded)}/{human_size(total)}  "
                    f"{human_size(int(speed))}/s  "
                    f"ETA {remain/60:.1f}min  ",
                    end="", flush=True
                )
            else:
                print(f"\r  Downloaded {human_size(downloaded)}...", end="", flush=True)

    print()  # newline
    if total and downloaded < total * 0.99:
        print(f"  [WARN] Only got {human_size(downloaded)} of {human_size(total)} — will retry next run.")
        return False

    tmp.rename(dest)
    return True


def main():
    print("=" * 60)
    print("  AfriHealth Assistant — Local LLM Model Downloader")
    print("=" * 60)
    print(f"\n  Model : Phi-3 Mini 4K Instruct (Q4_K_M)")
    print(f"  Size  : ~{MODEL_SIZE_GB} GB")
    print(f"  Dest  : {DEST_PATH}")
    print()

    if DEST_PATH.exists():
        size_mb = DEST_PATH.stat().st_size / 1024 / 1024
        print(f"  [OK] Model already exists ({size_mb:.0f} MB). Nothing to do.")
        print(f"\n  The backend will load it automatically on next start.")
        return 0

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    tmp_path = DEST_PATH.with_suffix(".tmp")
    if tmp_path.exists():
        size_mb = tmp_path.stat().st_size / 1024 / 1024
        print(f"  Found partial download ({size_mb:.0f} MB). Resuming...")
    else:
        print(f"  Starting fresh download from Hugging Face...")
    print(f"  Total size: ~{MODEL_SIZE_GB} GB. Keep internet connected.\n")

    try:
        t0 = time.time()
        ok = download_with_resume(MODEL_URL, DEST_PATH)
        if ok:
            elapsed = time.time() - t0
            size_mb = DEST_PATH.stat().st_size / 1024 / 1024
            print(f"\n  [SUCCESS] Downloaded {size_mb:.0f} MB in {elapsed/60:.1f} minutes.")
            print(f"  Saved to: {DEST_PATH}")
            print(f"\n  Now restart the backend to load the model:")
            print(f"    venv\\Scripts\\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")
            return 0
        else:
            print("\n  Download incomplete. Run this script again to resume.")
            return 1
    except KeyboardInterrupt:
        print("\n\n  [PAUSED] Download paused. Run again to resume from where it stopped.")
        return 1
    except Exception as exc:
        print(f"\n\n  [ERROR] {exc}")
        print("\n  Run the script again to retry. Or manually download:")
        print(f"    {MODEL_URL}")
        print(f"  Save to: {DEST_PATH}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
