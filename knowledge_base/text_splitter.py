"""
Text Splitter — splits raw document text into overlapping chunks
suitable for vector embedding and RAG retrieval.
Uses LangChain's RecursiveCharacterTextSplitter when available,
falls back to a built-in implementation otherwise.
"""

from typing import List, Dict
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter as _LCSplitter
    _LANGCHAIN_OK = True
except ImportError:
    _LANGCHAIN_OK = False
    logger.warning("langchain not installed — using built-in text splitter.")


class TextSplitter:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size    = chunk_size    or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        if _LANGCHAIN_OK:
            self._splitter = _LCSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
        else:
            self._splitter = None

    def split(self, text: str, source: str = "unknown") -> List[Dict]:
        """Split text into chunks. Returns list of {text, source, chunk_id}."""
        if not text.strip():
            return []

        if self._splitter:
            raw_chunks = self._splitter.split_text(text)
        else:
            raw_chunks = self._builtin_split(text)

        return [
            {"text": chunk, "source": source, "chunk_id": i}
            for i, chunk in enumerate(raw_chunks)
            if chunk.strip()
        ]

    def _builtin_split(self, text: str) -> List[str]:
        chunks, start = [], 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks


text_splitter = TextSplitter()
