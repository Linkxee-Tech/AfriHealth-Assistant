"""
Build Knowledge Base Script
Runs the full pipeline: load raw docs → chunk → embed → store in ChromaDB.

Usage:
    python scripts/build_knowledge_base.py
    python scripts/build_knowledge_base.py --clear   # wipe and rebuild
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.utils.logger import get_logger
from knowledge_base.builder import KnowledgeBaseBuilder
from knowledge_base.vector_store import vector_store

logger = get_logger("build_knowledge_base")


def main():
    parser = argparse.ArgumentParser(description="Build AfriHealth RAG knowledge base")
    parser.add_argument("--clear", action="store_true", help="Clear existing knowledge base before rebuild")
    args = parser.parse_args()

    if args.clear:
        logger.info("Clearing existing knowledge base …")
        vector_store.connect()
        vector_store.clear()
        logger.info("Knowledge base cleared.")

    builder = KnowledgeBaseBuilder()
    result  = builder.build()

    if result["status"] == "no_data":
        print("\n⚠️  No documents found in backend/data/raw_data/")
        print("   Run:  python scripts/download_datasets.py")
        print("   Or place PDF/TXT files manually in the raw_data/ subdirectories.\n")
    else:
        print(f"\n[SUCCESS] Knowledge base built successfully!")
        print(f"   Files processed : {result['files']}")
        print(f"   Chunks created  : {result['chunks']}")
        print(f"   Vectors stored  : {result['stored']}")
        print(f"   Time elapsed    : {result['elapsed_s']}s\n")


if __name__ == "__main__":
    main()
