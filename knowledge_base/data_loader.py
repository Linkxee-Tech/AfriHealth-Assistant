"""
Data Loader — scans raw_data/ directories and loads medical documents
(PDFs, TXTs) ready for chunking and embedding.
"""

import os
from pathlib import Path
from typing import List, Dict
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

RAW_DATA_DIRS = [
    "who_guidelines",
    "medical_handbooks",
    "drug_database",
    "local_health_data",
]

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


class DataLoader:
    def __init__(self, raw_data_path: str = None):
        self.raw_data_path = Path(raw_data_path or Path(settings.VECTOR_DB_PATH).parent.parent / "raw_data")

    def scan_files(self) -> List[Dict]:
        """Scan all raw_data sub-directories and return file metadata list."""
        files = []
        for subdir in RAW_DATA_DIRS:
            dir_path = self.raw_data_path / subdir
            if not dir_path.exists():
                logger.warning("Directory not found: %s", dir_path)
                continue
            for fp in dir_path.rglob("*"):
                if fp.suffix.lower() in SUPPORTED_EXTENSIONS and fp.is_file():
                    files.append({
                        "path": str(fp),
                        "filename": fp.name,
                        "source_dir": subdir,
                        "extension": fp.suffix.lower(),
                        "size_bytes": fp.stat().st_size,
                    })
        logger.info("Found %d documents across %d directories.", len(files), len(RAW_DATA_DIRS))
        return files

    def load_file_bytes(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    def load_all(self) -> List[Dict]:
        """Load all files and return list of {metadata + bytes}."""
        result = []
        for meta in self.scan_files():
            try:
                meta["bytes"] = self.load_file_bytes(meta["path"])
                result.append(meta)
            except Exception as exc:
                logger.error("Failed to load %s: %s", meta["path"], exc)
        return result


data_loader = DataLoader()
