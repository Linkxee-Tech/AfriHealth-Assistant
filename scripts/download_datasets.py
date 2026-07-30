"""
Download Datasets Script
Downloads WHO guidelines and other public medical documents into raw_data/.

Usage:
    python scripts/download_datasets.py
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("download_datasets")

RAW_DATA_BASE = Path(settings.VECTOR_DB_PATH).parent.parent / "raw_data"

# Public WHO PDFs (freely downloadable)
WHO_DOCUMENTS = [
    {
        "url": "https://apps.who.int/iris/rest/bitstreams/1346361/retrieve",
        "filename": "who_guidelines_malaria_2022.pdf",
        "subdir": "who_guidelines",
    },
    {
        "url": "https://apps.who.int/iris/rest/bitstreams/1399752/retrieve",
        "filename": "who_essential_medicines_list.pdf",
        "subdir": "drug_database",
    },
]


def _progress(block_num, block_size, total_size):
    if total_size > 0:
        pct = min(block_num * block_size / total_size * 100, 100)
        print(f"\r  Downloading ... {pct:.1f}%", end="", flush=True)


def download_datasets():
    downloaded, skipped, failed = 0, 0, 0
    for doc in WHO_DOCUMENTS:
        dest = RAW_DATA_BASE / doc["subdir"] / doc["filename"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            logger.info("Already exists: %s", dest.name)
            skipped += 1
            continue
        logger.info("Downloading %s ...", doc["filename"])
        try:
            req = urllib.request.Request(
                doc["url"],
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            )
            with urllib.request.urlopen(req) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                block_size = 8192
                block_num = 0
                with open(dest, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        block_num += 1
                        _progress(block_num, block_size, total_size)
            print()
            logger.info("Saved: %s", dest)
            downloaded += 1
        except Exception as exc:
            print()
            logger.error("Failed %s: %s", doc["filename"], exc)
            failed += 1

    logger.info(
        "Done. Downloaded: %d, Skipped: %d, Failed: %d",
        downloaded, skipped, failed,
    )
    if failed:
        raise RuntimeError(
            f"{failed} dataset download(s) failed. No placeholder data was created; "
            "retry or place verified source documents in backend/data/raw_data/."
        )
    logger.info(
        "\nManual data sources:\n"
        "  WHO Guidelines: https://www.who.int/publications\n"
        "  MIRIAD Dataset: https://www.csd.uwo.ca/~MIRIAD/\n"
        "  Place PDFs in:  backend/data/raw_data/who_guidelines/\n"
        "                  backend/data/raw_data/medical_handbooks/\n"
        "                  backend/data/raw_data/drug_database/"
    )


if __name__ == "__main__":
    download_datasets()
