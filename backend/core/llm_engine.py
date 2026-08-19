"""
LLM Engine â€” Hybrid support for local (llama.cpp) and remote (Hugging Face, Groq, Gemini) models.

Design:
  - Lazy-loads the model on first call (not at import time).
  - Falls back to a clearly-labelled stub when the model file is absent (dev/CI mode).
  - Exposes both blocking generate() and streaming stream_generate().
  - Supports local GGUF files via llama.cpp or remote APIs (Hugging Face, Groq, Gemini).
"""

import os
import time
import requests
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
    logger.warning("llama-cpp-python not installed â€” local LLM engine running in STUB mode.")

_HUGGINGFACE_AVAILABLE = False
try:
    from huggingface_hub import InferenceClient
    _HUGGINGFACE_AVAILABLE = True
except ImportError:
    logger.debug("huggingface-hub not installed â€” remote Hugging Face API unavailable.")


class LLMEngine:
    """Manages the LLM â€” either local GGUF via llama.cpp or remote API."""

    def __init__(
        self,
        model_path: str = None,
        n_threads: int = None,
        n_ctx: int = None,
        provider: str = None,
    ):
        self.provider = provider or settings.LLM_PROVIDER
        self._explicit_model_path = model_path is not None
        raw_path = model_path or settings.MODEL_PATH or ""
        # Keep URLs as raw strings â€” resolve_project_path mangles them on Windows
        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            self.model_path = raw_path
        else:
            self.model_path = str(resolve_project_path(raw_path)) if raw_path else ""
        self.n_threads  = n_threads  or settings.NUM_THREADS
        self.n_ctx      = n_ctx      or settings.CONTEXT_LENGTH
        self._model     = None
        self._loaded    = False
        self._load_time_ms: float = 0.0
        self._load_error: Optional[str] = None
        
        logger.info("LLM Engine initialized with provider: %s", self.provider)

    # ------------------------------------------------------------------
    def load_model(self) -> bool:
        """Load the model â€” either local GGUF or remote API. Returns True on success."""
        if self._loaded:
            return True

        t0 = time.perf_counter()

        # Remote providers don't require "loading" â€” just validate API keys
        if self.provider == "huggingface":
            return self._load_huggingface(t0)
        elif self.provider == "groq":
            return self._load_groq(t0)
        elif self.provider == "gemini":
            return self._load_gemini(t0)
        else:
            # Default to local llama.cpp
            return self._load_local(t0)

    def _load_huggingface(self, t0: float) -> bool:
        """Load Hugging Face Inference API client."""
        if not _HUGGINGFACE_AVAILABLE:
            self._load_error = "huggingface-hub not installed. Install with: pip install huggingface-hub"
            self._loaded = True
            logger.error(self._load_error)
            return False

        if not settings.HUGGINGFACE_API_KEY:
            self._load_error = "HUGGINGFACE_API_KEY not set in .env. Get one free at huggingface.co"
            self._loaded = True
            logger.warning(self._load_error)
            return False

        try:
            self._model = InferenceClient(
                api_key=settings.HUGGINGFACE_API_KEY,
                model=settings.HUGGINGFACE_MODEL_ID,
            )
            self._load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            self._loaded = True
            self._load_error = None
            logger.info("Hugging Face Inference API client loaded in %.0f ms", self._load_time_ms)
            return True
        except Exception as exc:
            self._load_error = str(exc)
            self._loaded = True
            logger.error("Failed to initialize Hugging Face client: %s", exc)
            return False

    def _load_groq(self, t0: float) -> bool:
        """Load Groq API client."""
        if not settings.GROQ_API_KEY:
            self._load_error = "GROQ_API_KEY not set in .env. Get one free at groq.com"
            self._loaded = True
            logger.warning(self._load_error)
            return False

        try:
            from groq import Groq
            self._model = Groq(api_key=settings.GROQ_API_KEY)
            self._load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            self._loaded = True
            self._load_error = None
            logger.info("Groq API client loaded in %.0f ms", self._load_time_ms)
            return True
        except ImportError:
            self._load_error = "groq not installed. Install with: pip install groq"
            self._loaded = True
            logger.error(self._load_error)
            return False
        except Exception as exc:
            self._load_error = str(exc)
            self._loaded = True
            logger.error("Failed to initialize Groq client: %s", exc)
            return False

    def _load_gemini(self, t0: float) -> bool:
        """Load Google Gemini client."""
        if not settings.GEMINI_API_KEY:
            self._load_error = "GEMINI_API_KEY not set in .env"
            self._loaded = True
            logger.warning(self._load_error)
            return False

        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel("gemini-pro")
            self._load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            self._loaded = True
            self._load_error = None
            logger.info("Gemini API client loaded in %.0f ms", self._load_time_ms)
            return True
        except ImportError:
            self._load_error = "google-generativeai not installed. Install with: pip install google-generativeai"
            self._loaded = True
            logger.error(self._load_error)
            return False
        except Exception as exc:
            self._load_error = str(exc)
            self._loaded = True
            logger.error("Failed to initialize Gemini client: %s", exc)
            return False

    def _load_local(self, t0: float) -> bool:
        """Load local GGUF model via llama.cpp."""
        if not _MODEL_AVAILABLE:
            logger.warning("llama-cpp-python not available â€” stub mode.")
            self._load_error = "llama-cpp-python is not installed"
            self._loaded = True
            return False

        import sys
        is_testing = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
        model_file = None
        
        # 1. Resolve the requested local model. If the caller passed a specific
        # missing path, do not silently load a different fallback model.
        local_fallback = Path(resolve_project_path("models/llm/phi-3-mini-q4.gguf"))
        fallback_paths = [
            str(local_fallback),
            "D:/Phi-3-mini-4k-instruct-q4.gguf",
            "D:/Phi-3-mini-4k-instruct-q4.GGUF",
            "D:/phi-3-mini-q4.gguf",
            "D:/phi-3-mini.gguf",
        ]
        fallbacks = []
        if self.model_path and not self.model_path.startswith("http"):
            fallbacks.append(self.model_path)
            if not self._explicit_model_path:
                fallbacks.extend(fallback_paths)
        elif not self._explicit_model_path and not self.model_path.startswith("http"):
            fallbacks.extend(fallback_paths)
        for fb in fallbacks:
            fb_path = Path(fb)
            if fb_path.exists():
                self.model_path = str(fb_path)
                model_file = fb_path
                logger.info("Found local model file at %s", fb_path)
                break

        # 2. If explicitly enabled, download a remote HuggingFace GGUF.
        # Chat requests must not block on multi-GB downloads by default.
        if not model_file and self.model_path and "huggingface.co" in self.model_path:
            if not settings.AUTO_DOWNLOAD_MODEL:
                logger.warning(
                    "Local model not found and AUTO_DOWNLOAD_MODEL is disabled - stub mode."
                )
                self._load_error = (
                    "Local model not found; set AUTO_DOWNLOAD_MODEL=true to download from HuggingFace"
                )
                self._loaded = True
                return False
            logger.info("Local model not found. HuggingFace URL detected. Downloading model automatically...")
            try:
                import urllib.parse
                from huggingface_hub import hf_hub_download
                parsed = urllib.parse.urlparse(self.model_path)
                parts = parsed.path.strip('/').split('/')
                if "resolve" in parts:
                    idx = parts.index("resolve")
                    repo_id = "/".join(parts[:idx])
                else:
                    repo_id = "/".join(parts[:2])
                filename = parts[-1]
                logger.info("Fetching %s from %s ...", filename, repo_id)
                
                cached_path = hf_hub_download(
                    repo_id=repo_id, 
                    filename=filename, 
                    token=settings.HUGGINGFACE_API_KEY if settings.HUGGINGFACE_API_KEY else None
                )
                self.model_path = cached_path
                model_file = Path(cached_path)
            except Exception as e:
                logger.warning("Failed to download model from HuggingFace (offline?): %s", e)
                # hf_hub_download might fail if offline and not cached.
                self._load_error = f"Failed to download model from HuggingFace: {e}"
                self._loaded = True
                return False

        if not model_file or not model_file.exists():
            logger.warning("Model file not found at %s â€” stub mode.", self.model_path)
            self._load_error = f"Model file not found: {self.model_path}"
            self._loaded = True
            return False

        # Validate GGUF format
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
            logger.info("Loading model from %s â€¦", self.model_path)
            load_kwargs = {
                "model_path": self.model_path,
                "n_threads": self.n_threads,
                "n_ctx": self.n_ctx,
                "verbose": settings.DEBUG,
            }
            try:
                self._model = Llama(**load_kwargs)
            except Exception as first_exc:
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
            self._loaded = True
            return False

    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
        system_prompt: str = None,
    ) -> str:
        """Blocking generation â€” supports local, Hugging Face, Groq, or Gemini."""
        if not self._loaded:
            self.load_model()

        max_tokens = max_tokens if max_tokens is not None else settings.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
        top_p = top_p if top_p is not None else settings.DEFAULT_TOP_P

        if self._model is None:
            return self._stub_response(prompt)

        try:
            if self.provider == "huggingface":
                return self._generate_huggingface(prompt, max_tokens, temperature, top_p)
            elif self.provider == "groq":
                return self._generate_groq(prompt, max_tokens, temperature, top_p)
            elif self.provider == "gemini":
                return self._generate_gemini(prompt, max_tokens, temperature, top_p)
            else:
                # Local llama.cpp â€” use chat_completion so system_prompt is respected
                return self._generate_local(prompt, max_tokens, temperature, top_p, system_prompt=system_prompt)
        except Exception as exc:
            logger.error("LLM generation error: %s", exc)
            return f"[LLM error: {exc}]"

    def _generate_local(self, prompt: str, max_tokens: int, temperature: float, top_p: float, system_prompt: str = None) -> str:
        """Generate using local llama.cpp chat_completion so system_prompt language is enforced."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        output = self._model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=["User:", "\n\nUser:", "Human:"],
        )
        return output["choices"][0]["message"]["content"].strip()

    def _generate_huggingface(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> str:
        """Generate using Hugging Face Inference API."""
        response = self._model.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.HUGGINGFACE_MODEL_ID,
            max_tokens=max_tokens,
            temperature=max(temperature, 0.01),
            top_p=top_p,
        )
        return response.choices[0].message.content.strip()

    def _generate_groq(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> str:
        """Generate using Groq API."""
        message = self._model.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3-8b-instantiate",  # or llama-2-7b-chat
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        return message.choices[0].message.content.strip()

    def _generate_gemini(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> str:
        """Generate using Google Gemini API."""
        response = self._model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            },
        )
        return response.text.strip()

    # ------------------------------------------------------------------
    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
        system_prompt: str = None,
    ) -> Generator[str, None, None]:
        """Streaming generation â€” yields text chunks as they are produced."""
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
            if self.provider == "huggingface":
                for chunk in self._stream_huggingface(prompt, max_tokens, temperature, top_p):
                    yield chunk
            elif self.provider == "groq":
                for chunk in self._stream_groq(prompt, max_tokens, temperature, top_p):
                    yield chunk
            elif self.provider == "gemini":
                for chunk in self._stream_gemini(prompt, max_tokens, temperature, top_p):
                    yield chunk
            else:
                # Local llama.cpp â€” pass system_prompt so language is enforced
                for chunk in self._stream_local(prompt, max_tokens, temperature, top_p, system_prompt=system_prompt):
                    yield chunk
        except (StopIteration, RuntimeError) as exc:
            # Python 3.7+: StopIteration inside a generator becomes RuntimeError
            logger.warning("Stream exhausted (StopIteration/RuntimeError): %s", exc)
        except Exception as exc:
            logger.error("LLM stream error: %s", exc)
            yield f"[LLM stream error: {exc}]"

    def _stream_local(self, prompt: str, max_tokens: int, temperature: float, top_p: float, system_prompt: str = None) -> Generator[str, None, None]:
        """Stream using local llama.cpp chat_completion so language system_prompt is enforced."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        stream = self._model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=["User:", "\n\nUser:", "Human:"],
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            token = delta.get("content", "")
            if token:
                yield token

    def _stream_huggingface(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> Generator[str, None, None]:
        """Stream using Hugging Face Inference API."""
        try:
            stream = self._model.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.HUGGINGFACE_MODEL_ID,
                max_tokens=max_tokens,
                temperature=max(temperature, 0.01),  # HF requires > 0
                top_p=top_p,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            logger.warning("HuggingFace stream error: %s", exc)
            # Fall back to non-streaming call
            try:
                result = self._model.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=settings.HUGGINGFACE_MODEL_ID,
                    max_tokens=max_tokens,
                    temperature=max(temperature, 0.01),
                    top_p=top_p,
                )
                if result and result.choices:
                    content = result.choices[0].message.content
                    words = content.split()
                    import time as _time
                    for i, w in enumerate(words):
                        _time.sleep(0.01)
                        yield w + (" " if i < len(words) - 1 else "")
            except Exception as e2:
                logger.error("HuggingFace fallback also failed: %s", e2)
                yield f"[HuggingFace error: {e2}]"

    def _stream_groq(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> Generator[str, None, None]:
        """Stream using Groq API."""
        stream = self._model.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3-8b-instantiate",
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_gemini(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> Generator[str, None, None]:
        """Stream using Google Gemini API."""
        response = self._model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            },
            stream=True,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

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
