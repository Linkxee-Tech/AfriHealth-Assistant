"""
Document processor — loads PDFs, DOCX, TXT, and images (via OCR),
then chunks the extracted text into overlapping segments for RAG.
"""

import io
from pathlib import Path
from typing import List, Dict

from backend.core.rag_engine import rag_engine
from backend.core.ocr_engine import ocr_engine
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Optional heavy deps — degrade gracefully if not installed
try:
    import pypdf; _PDF_OK = True
except ImportError:
    _PDF_OK = False; logger.warning("pypdf not installed — PDF loading disabled.")

try:
    import docx as _docx; _DOCX_OK = True
except ImportError:
    _DOCX_OK = False; logger.warning("python-docx not installed — DOCX loading disabled.")

try:
    import easyocr; _OCR_OK = True
except ImportError:
    _OCR_OK = False; logger.warning("easyocr not installed — image OCR disabled.")


class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size    = chunk_size    or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self._ocr_reader   = None

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------
    def load_pdf(self, file_bytes: bytes) -> str:
        if not _PDF_OK:
            return "[PDF support unavailable — install pypdf]"
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages  = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages).strip()
        except Exception as exc:
            logger.error("PDF load error: %s", exc)
            return ""

    def load_text(self, file_bytes: bytes) -> str:
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception as exc:
            logger.error("Text load error: %s", exc)
            return ""

    def load_docx(self, file_bytes: bytes) -> str:
        if not _DOCX_OK:
            return "[DOCX support unavailable — install python-docx]"
        try:
            doc  = _docx.Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error("DOCX load error: %s", exc)
            return ""

    def load_image(self, file_bytes: bytes) -> str:
        """Extract text from an image using easyOCR."""
        if not _OCR_OK:
            return "[Image OCR unavailable — install easyocr]"
        try:
            if self._ocr_reader is None:
                logger.info("Initialising easyOCR reader …")
                self._ocr_reader = easyocr.Reader(["en"], gpu=False)
            results = self._ocr_reader.readtext(file_bytes, detail=0)
            return " ".join(results).strip()
        except Exception as exc:
            logger.error("OCR error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------
    def chunk_document(self, text: str) -> List[Dict]:
        """Split text into overlapping chunks with metadata."""
        if not text.strip():
            return []
        chunks = []
        start  = 0
        idx    = 0
        while start < len(text):
            end   = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append({"chunk_id": idx, "text": chunk, "start": start, "end": end})
            start += self.chunk_size - self.chunk_overlap
            idx   += 1
        return chunks

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def process_document(self, file_bytes: bytes, filename: str, file_type: str = None) -> Dict:
        """Detect file type, extract text, chunk, return metadata dict."""
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            text = self.load_pdf(file_bytes)
        elif ext in (".docx", ".doc"):
            text = self.load_docx(file_bytes)
        elif ext == ".txt" or ext == ".md" or file_type == "text/plain":
            text = self.load_text(file_bytes)
        elif ext in (".jpg", ".jpeg", ".png", ".bmp") or file_type in (
            "image/jpeg", "image/png", "image/bmp"
        ):
            # Use OCR Engine for images
            text = ocr_engine.extract_text(file_bytes)
        else:
            text = f"[Unsupported file type: {file_type}]"

        chunks = self.chunk_document(text)
        return {
            "filename": filename,
            "file_type": ext.lstrip("."),
            "raw_text": text,
            "chunks": chunks,
            "chunk_count": len(chunks),
        }


document_processor = DocumentProcessor()
