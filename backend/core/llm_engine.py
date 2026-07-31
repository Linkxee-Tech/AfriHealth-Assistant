"""
LLM Engine — wraps llama.cpp (via llama-cpp-python) for offline inference.

Design:
  - Lazy-loads the model on first call (not at import time).
  - Falls back to a clearly-labelled stub when the model file is absent
    (dev/CI mode) so all other modules stay testable.
  - Exposes both blocking generate() and streaming stream_generate().
"""

import os
import time
from pathlib import Path
from typing import Generator, Optional

from backend.config import settings, resolve_project_path
from backend.utils.logger import get_logger
from backend.utils.metrics import collect_system_metrics

logger = get_logger(__name__)

_MODEL_AVAILABLE = False
try:
    from llama_cpp import Llama
    _MODEL_AVAILABLE = True
except ImportError:
    logger.warning("llama-cpp-python not installed — LLM engine running in STUB mode.")


class LLMEngine:
    """Manages the 4-bit quantised LLM via llama.cpp."""

    def __init__(
        self,
        model_path: str = None,
        n_threads: int = None,
        n_ctx: int = None,
    ):
        self.model_path = str(resolve_project_path(model_path or settings.MODEL_PATH))
        self.n_threads  = n_threads  or settings.NUM_THREADS
        self.n_ctx      = n_ctx      or settings.CONTEXT_LENGTH
        self._model     = None
        self._loaded    = False
        self._load_time_ms: float = 0.0
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------
    def load_model(self) -> bool:
        """Load the quantised GGUF model. Returns True on success."""
        if self._loaded:
            return True

        if not _MODEL_AVAILABLE:
            logger.warning("llama-cpp-python not available — stub mode.")
            self._load_error = "llama-cpp-python is not installed"
            self._loaded = True   # mark as "loaded" so stubs work
            return False

        import sys
        is_testing = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)

        model_file = Path(self.model_path)
        if not model_file.exists() and not is_testing and "missing-model" not in self.model_path:
            # 1. Check local model/ folder relative to project root (auditing directory)
            local_fallback = Path(resolve_project_path("model/Phi-3-mini-4k-instruct-q4.gguf"))
            if local_fallback.exists():
                self.model_path = str(local_fallback)
                model_file = local_fallback
                logger.info("Found local model file at %s", local_fallback)
            else:
                # 2. Check common fallbacks on D: drive for convenience
                fallbacks = [
                    "D:/Phi-3-mini-4k-instruct-q4.gguf",
                    "D:/Phi-3-mini-4k-instruct-q4.GGUF",
                    "D:/phi-3-mini-q4.gguf",
                    "D:/phi-3-mini.gguf",
                ]
                for fb in fallbacks:
                    fb_path = Path(fb)
                    if fb_path.exists():
                        self.model_path = fb
                        model_file = fb_path
                        logger.info("Found fallback model file at %s", fb)
                        break

        if not model_file.exists():
            logger.warning("Model file not found at %s — stub mode.", self.model_path)
            self._load_error = f"Model file not found: {self.model_path}"
            self._loaded = True
            return False

        # Fail early with a useful configuration error instead of passing a
        # placeholder/text file to llama.cpp. GGUF files always start with
        # the four-byte magic value below.
        try:
            with model_file.open("rb") as handle:
                magic = handle.read(4)
            if magic != b"GGUF":
                self._load_error = (
                    f"Invalid GGUF model file at {model_file}: expected GGUF header, "
                    f"found {magic!r}"
                )
                logger.error(self._load_error)
                self._loaded = True
                return False
        except OSError as exc:
            self._load_error = f"Unable to read model file {model_file}: {exc}"
            logger.error(self._load_error)
            self._loaded = True
            return False

        try:
            t0 = time.perf_counter()
            logger.info("Loading model from %s …", self.model_path)
            load_kwargs = {
                "model_path": self.model_path,
                "n_threads": self.n_threads,
                "n_ctx": self.n_ctx,
                "verbose": settings.DEBUG,
            }
            try:
                self._model = Llama(**load_kwargs)
            except Exception as first_exc:
                # A memory-mapped load can fail for valid files on some disks
                # with Windows in-page/read errors. Retry using a normal read
                # before falling back to stub mode.
                logger.warning("Memory-mapped model load failed: %s; retrying without mmap.", first_exc)
                self._model = Llama(**load_kwargs, use_mmap=False)
            self._load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            self._loaded = True
            self._load_error = None
            logger.info("Model loaded in %.0f ms", self._load_time_ms)
            return True
        except Exception as exc:
            logger.error("Failed to load model: %s", exc)
            self._load_error = str(exc)
            self._loaded = True   # still mark loaded so app doesn't retry endlessly
            return False

    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
    ) -> str:
        """Blocking generation. Returns the full response string."""
        if not self._loaded:
            self.load_model()

        max_tokens = max_tokens if max_tokens is not None else settings.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
        top_p = top_p if top_p is not None else settings.DEFAULT_TOP_P

        if self._model is None:
            return self._stub_response(prompt)

        try:
            output = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=["User:", "\n\nUser:", "Human:"],
                echo=False,
            )
            return output["choices"][0]["text"].strip()
        except Exception as exc:
            logger.error("LLM generation error: %s", exc)
            return f"[LLM error: {exc}]"

    # ------------------------------------------------------------------
    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
    ) -> Generator[str, None, None]:
        """Streaming generation — yields text chunks as they are produced."""
        if not self._loaded:
            self.load_model()

        max_tokens = max_tokens if max_tokens is not None else settings.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
        top_p = top_p if top_p is not None else settings.DEFAULT_TOP_P

        if self._model is None:
            for chunk in self._stub_stream(prompt):
                yield chunk
            return

        try:
            stream = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=["User:", "\n\nUser:", "Human:"],
                echo=False,
                stream=True,
            )
            for chunk in stream:
                token = chunk["choices"][0]["text"]
                if token:
                    yield token
        except Exception as exc:
            logger.error("LLM stream error: %s", exc)
            yield f"[LLM stream error: {exc}]"

    # ------------------------------------------------------------------
    def get_memory_usage(self) -> float:
        """Return current process memory usage in GB."""
        try:
            import psutil, os
            proc = psutil.Process(os.getpid())
            return round(proc.memory_info().rss / 1024 ** 3, 2)
        except Exception:
            return 0.0

    def get_status(self) -> dict:
        return {
            "model_loaded": self._loaded and self._model is not None,
            "model_path": self.model_path,
            "model_file_exists": Path(self.model_path).exists(),
            "load_time_ms": self._load_time_ms,
            "load_error": self._load_error,
            "memory_usage_gb": self.get_memory_usage(),
            "stub_mode": self._model is None,
            **collect_system_metrics(),
        }

    # ------------------------------------------------------------------
    # Stubs for dev/CI when model file is not present
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_context(raw: str) -> str:
        """Strip source labels and tidy up raw RAG context into readable paragraphs."""
        import re
        # Remove [Source: ...] labels
        cleaned = re.sub(r'\[Source:[^\]]*\]', '', raw)
        # Collapse excessive whitespace / newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        # Remove leftover dashes used as section dividers
        cleaned = re.sub(r'^-{3,}\s*$', '', cleaned, flags=re.MULTILINE)
        # Strip leading/trailing whitespace per line
        lines = [l.rstrip() for l in cleaned.splitlines()]
        # Remove blank lines at start/end
        cleaned = '\n'.join(lines).strip()
        return cleaned

    @staticmethod
    def _stub_response(prompt: str) -> str:
        """Return a clean, humanized answer from RAG context when no AI model is loaded."""
        context_block = ""

        # Primary format from RAG_PROMPT_TEMPLATE:
        # --- RETRIEVED CONTEXT ---\n{context}\n--- END CONTEXT ---
        if "--- RETRIEVED CONTEXT ---" in prompt:
            try:
                part = prompt.split("--- RETRIEVED CONTEXT ---", 1)[1]
                if "--- END CONTEXT ---" in part:
                    part = part.split("--- END CONTEXT ---", 1)[0]
                context_block = part.strip()
            except Exception:
                pass

        # Hybrid orchestrator inline format:
        # --- OFFLINE MEDICAL KNOWLEDGE ---\n...\n\n--- ONLINE WEB SEARCH
        if not context_block and "--- OFFLINE MEDICAL KNOWLEDGE ---" in prompt:
            try:
                part = prompt.split("--- OFFLINE MEDICAL KNOWLEDGE ---", 1)[1]
                if "--- ONLINE WEB SEARCH" in part:
                    part = part.split("--- ONLINE WEB SEARCH", 1)[0]
                context_block = part.strip()
            except Exception:
                pass

        # Remove empty placeholder
        if context_block and context_block.strip() in ("", "No specific offline knowledge found."):
            context_block = ""

        if context_block:
            clean = LLMEngine._clean_context(context_block)
            return (
                f"{clean}\n\n"
                "Please note: this information comes directly from our indexed medical knowledge base. "
                "For a fully summarised answer, please add a valid Gemini API key or install the local AI model."
            )

        return (
            "I was not able to find specific information about that in the medical knowledge base. "
            "Please try rephrasing your question or consult a qualified healthcare professional for accurate advice."
        )

    @staticmethod
    def _stub_stream(prompt: str) -> Generator[str, None, None]:
        words = LLMEngine._stub_response(prompt).split()
        for i, w in enumerate(words):
            import time; time.sleep(0.015)
            yield w + (" " if i < len(words) - 1 else "")


# Singleton
llm_engine = LLMEngine()
