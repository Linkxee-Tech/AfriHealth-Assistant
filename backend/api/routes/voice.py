"""
Voice routes — POST /voice/transcribe
Uses faster-whisper (offline) or falls back to a Google Speech API stub.
"""
import io
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.api.dependencies.auth import get_current_user
from backend.utils.logger import get_logger

logger = get_logger(__name__)
voice_router = APIRouter(prefix="/voice", tags=["Voice"])


_whisper_model = None


def _transcribe_with_whisper(audio_bytes: bytes, content_type: str = "audio/wav") -> str:
    """Transcribe audio using faster-whisper (offline)."""
    global _whisper_model
    try:
        from faster_whisper import WhisperModel
        if _whisper_model is None:
            # Use tiny model for speed on CPU; downloads ~75MB on first use
            _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        model = _whisper_model
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, _ = model.transcribe(tmp_path, language=None, beam_size=5)
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip()
        finally:
            os.unlink(tmp_path)
    except ImportError:
        raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")
    except Exception as exc:
        raise RuntimeError(f"Whisper transcription failed: {exc}")


@voice_router.post("/transcribe", summary="Transcribe voice audio to text")
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, WEBM, OGG)"),
    current_user=Depends(get_current_user),
):
    """
    Accepts an audio file and returns the transcribed text.
    Uses faster-whisper offline by default. If Whisper fails or runs out of memory,
    falls back to Gemini Cloud transcription if configured.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25 MB limit
        raise HTTPException(status_code=413, detail="Audio file too large (max 25 MB)")
        
    # Try Whisper first
    try:
        text = _transcribe_with_whisper(audio_bytes, audio.content_type or "audio/wav")
        if text:
            return {"text": text, "language_detected": "auto", "engine": "whisper_local"}
    except Exception as whisper_exc:
        logger.warning("Whisper transcription failed (falling back to Gemini if configured): %s", whisper_exc)
        
    # Fallback to Gemini if configured
    from backend.core.gemini_integration import gemini_client
    if gemini_client.is_configured:
        try:
            logger.info("Using Gemini for audio transcription fallback...")
            from google.genai import types
            mime = audio.content_type or "audio/wav"
            
            # Map common webm/wav types if empty/invalid
            if not mime or mime == "application/octet-stream":
                mime = "audio/wav"
                
            response = gemini_client._client.models.generate_content(
                model=gemini_client.model_name,
                contents=[
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type=mime,
                    ),
                    "Transcribe this audio file exactly into text. Do not add any summary, notes, or comments. Just write the transcription."
                ]
            )
            text = response.text.strip()
            if text:
                return {"text": text, "language_detected": "auto", "engine": "gemini_cloud"}
        except Exception as gemini_exc:
            logger.error("Gemini fallback transcription also failed: %s", gemini_exc)
            
    # If both failed or Gemini is not configured, throw a clear exception
    raise HTTPException(
        status_code=500,
        detail="Speech-to-text service is currently unavailable. Whisper failed to allocate memory and Gemini cloud fallback is either not configured or failed."
    )
