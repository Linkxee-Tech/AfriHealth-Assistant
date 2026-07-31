"""
Download Models Script
Downloads the configured Phi-3 Mini GGUF model and all-MiniLM-L6-v2 embeddings.

Usage:
    python scripts/download_models.py
    python scripts/download_models.py --embedding-only
    python scripts/download_models.py --llm-only
"""

import argparse
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import settings, resolve_project_path
from backend.utils.logger import get_logger

logger = get_logger("download_models")

LLM_MODEL_URL = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def _is_valid_gguf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"GGUF" and path.stat().st_size > 1024 * 1024
    except OSError:
        return False


def _progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        bar = "█" * int(pct / 2)
        print(f"\r  [{bar:<50}] {pct:.1f}%", end="", flush=True)


def download_llm():
    dest = resolve_project_path(settings.MODEL_PATH)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and _is_valid_gguf(dest):
        logger.info("Valid GGUF model already exists at %s", dest)
        return
    if dest.exists():
        logger.error("Refusing to use invalid/non-GGUF model file at %s", dest)
        return

    logger.info("Downloading LLM model (~4.6 GB) …")
    logger.info("Source: %s", LLM_MODEL_URL)
    logger.info("Destination: %s", dest)
    try:
        tmp_dest = dest.with_suffix(dest.suffix + ".download")
        urllib.request.urlretrieve(LLM_MODEL_URL, str(tmp_dest), reporthook=_progress)
        print()
        if not _is_valid_gguf(tmp_dest):
            tmp_dest.unlink(missing_ok=True)
            raise RuntimeError("Downloaded file is not a valid GGUF model")
        tmp_dest.replace(dest)
        logger.info("LLM model downloaded successfully.")
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        logger.error(
            "Manual download:\n  1. Visit https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF\n"
            "  2. Download Llama-3.2-3B-Instruct-Q4_K_M.gguf\n"
            "  3. Place it at: %s", dest
        )


def download_embedding_model():
    dest = Path(settings.EMBEDDING_MODEL)
    if dest.exists() and any(dest.iterdir()):
        logger.info("Embedding model already exists at %s", dest)
        return
    dest.mkdir(parents=True, exist_ok=True)
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Downloading embedding model %s …", EMBEDDING_MODEL_NAME)
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        model.save(str(dest))
        logger.info("Embedding model saved to %s", dest)
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
    except Exception as exc:
        logger.error("Embedding model download failed: %s", exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download AfriHealth models")
    parser.add_argument("--llm-only",       action="store_true")
    parser.add_argument("--embedding-only", action="store_true")
    args = parser.parse_args()

    if args.embedding_only:
        download_embedding_model()
    elif args.llm_only:
        download_llm()
    else:
        download_llm()
        download_embedding_model()
