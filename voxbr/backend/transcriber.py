import os
import time
from loguru import logger

# Whisper model is loaded once and reused
_whisper_model = None
WHISPER_MODEL_SIZE = "base"


def get_whisper_model():
    """Load and cache the Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}'...")
        start = time.time()
        import whisper
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
        elapsed = time.time() - start
        logger.info(f"Whisper model loaded in {elapsed:.1f}s")
    return _whisper_model


def transcribe(file_path: str, language: str = "pt") -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Args:
        file_path: Absolute path to the audio file.
        language: ISO language code (e.g. 'pt', 'en', 'es').

    Returns:
        dict with keys:
            text (str): Full transcription text.
            duration (float): Estimated audio duration in seconds.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    model = get_whisper_model()
    logger.info(f"Transcribing file: {file_path} | language hint: {language}")

    start = time.time()
    try:
        result = model.transcribe(
            file_path,
            language=language,
            verbose=False,
            fp16=False,  # fp16 may cause issues on CPU
        )
    except Exception as e:
        logger.warning(f"Transcription with language={language} failed: {e}. Retrying without language hint.")
        result = model.transcribe(file_path, verbose=False, fp16=False)

    elapsed = time.time() - start
    transcript_text = result.get("text", "").strip()
    segments = result.get("segments", [])

    # Calculate duration from segments if available
    if segments:
        duration = segments[-1].get("end", elapsed)
    else:
        # Fallback: estimate from file size (very rough)
        file_size = os.path.getsize(file_path)
        duration = file_size / 16000  # rough estimate at 128kbps

    logger.info(
        f"Transcription complete in {elapsed:.1f}s | "
        f"duration={duration:.1f}s | "
        f"chars={len(transcript_text)}"
    )

    return {
        "text": transcript_text,
        "duration": round(duration, 2),
    }
