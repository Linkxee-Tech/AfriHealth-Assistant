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

from backend.config import settings
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
        self.model_path = model_path or settings.MODEL_PATH
        self.n_threads  = n_threads  or settings.NUM_THREADS
        self.n_ctx      = n_ctx      or settings.CONTEXT_LENGTH
        self._model     = None
        self._loaded    = False
        self._load_time_ms: float = 0.0

    # ------------------------------------------------------------------
    def load_model(self) -> bool:
        """Load the quantised GGUF model. Returns True on success."""
        if self._loaded:
            return True

        if not _MODEL_AVAILABLE:
            logger.warning("llama-cpp-python not available — stub mode.")
            self._loaded = True   # mark as "loaded" so stubs work
            return False

        if not Path(self.model_path).exists():
            logger.warning("Model file not found at %s — stub mode.", self.model_path)
            self._loaded = True
            return False

        try:
            t0 = time.perf_counter()
            logger.info("Loading model from %s …", self.model_path)
            self._model = Llama(
                model_path=self.model_path,
                n_threads=self.n_threads,
                n_ctx=self.n_ctx,
                verbose=settings.DEBUG,
            )
            self._load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            self._loaded = True
            logger.info("Model loaded in %.0f ms", self._load_time_ms)
            return True
        except Exception as exc:
            logger.error("Failed to load model: %s", exc)
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

        max_tokens  = max_tokens  or settings.DEFAULT_MAX_TOKENS
        temperature = temperature or settings.DEFAULT_TEMPERATURE
        top_p       = top_p       or settings.DEFAULT_TOP_P

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

        max_tokens  = max_tokens  or settings.DEFAULT_MAX_TOKENS
        temperature = temperature or settings.DEFAULT_TEMPERATURE
        top_p       = top_p       or settings.DEFAULT_TOP_P

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
            "memory_usage_gb": self.get_memory_usage(),
            "stub_mode": self._model is None,
            **collect_system_metrics(),
        }

    # ------------------------------------------------------------------
    # Stubs for dev/CI when model file is not present
    # ------------------------------------------------------------------
    @staticmethod
    def _stub_response(prompt: str) -> str:
        return (
            "(Stub mode — llama.cpp model not loaded)\n\n"
            "This is a placeholder response. "
            "Please download the quantised GGUF model and place it at the "
            "path specified in MODEL_PATH. "
            "Once the model is loaded, real AI responses will appear here."
        )

    @staticmethod
    def _stub_stream(prompt: str) -> Generator[str, None, None]:
        words = LLMEngine._stub_response(prompt).split()
        for i, w in enumerate(words):
            import time; time.sleep(0.02)
            yield w + (" " if i < len(words) - 1 else "")


# Singleton
llm_engine = LLMEngine()
