import os
import json
import re
from loguru import logger

MISTRAL_MODEL = "mistral-small-latest"

LANGUAGE_NAMES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
}


def _get_language_name(language: str) -> str:
    return LANGUAGE_NAMES.get(language.lower(), language)


def _fallback_summary(transcript: str) -> dict:
    """Generate a basic summary without AI when no API key is available."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", transcript) if s.strip()]

    if not sentences:
        return {
            "summary": "Transcrição sem conteúdo detectado.",
            "key_points": [],
        }

    # Use first 3 sentences as summary
    summary_sentences = sentences[:3]
    summary = ". ".join(summary_sentences)
    if not summary.endswith("."):
        summary += "."

    # Use next sentences as key points (up to 5)
    key_point_sentences = sentences[3:8]
    if not key_point_sentences:
        key_point_sentences = sentences[:min(5, len(sentences))]

    key_points = [s if s.endswith(".") else s + "." for s in key_point_sentences]

    logger.warning("MISTRAL_API_KEY not set — using fallback summary generator")
    return {
        "summary": summary,
        "key_points": key_points[:5],
    }


def _parse_ai_response(content: str) -> dict:
    """Parse the AI response JSON, with fallback for malformed output."""
    # Try direct JSON parse first
    try:
        data = json.loads(content)
        return {
            "summary": str(data.get("summary", "")),
            "key_points": [str(p) for p in data.get("key_points", [])],
        }
    except json.JSONDecodeError:
        pass

    # Try to extract JSON block from markdown-wrapped response
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            return {
                "summary": str(data.get("summary", "")),
                "key_points": [str(p) for p in data.get("key_points", [])],
            }
        except json.JSONDecodeError:
            pass

    # Last resort: find raw JSON object in the text
    json_obj_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_obj_match:
        try:
            data = json.loads(json_obj_match.group(0))
            return {
                "summary": str(data.get("summary", "")),
                "key_points": [str(p) for p in data.get("key_points", [])],
            }
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse AI response as JSON, using raw text as summary")
    return {
        "summary": content[:500],
        "key_points": [],
    }


def summarize(transcript: str, language: str = "pt") -> dict:
    """
    Summarize a transcript using Mistral AI.

    Args:
        transcript: The full transcription text.
        language: ISO language code for the response language.

    Returns:
        dict with keys:
            summary (str): Concise summary of the transcript.
            key_points (list[str]): 3-5 main points from the transcript.
    """
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        return _fallback_summary(transcript)

    language_name = _get_language_name(language)

    # Truncate very long transcripts to avoid token limits
    max_chars = 8000
    truncated = transcript[:max_chars]
    if len(transcript) > max_chars:
        truncated += "\n\n[... texto truncado ...]"
        logger.warning(f"Transcript truncated from {len(transcript)} to {max_chars} chars for summarization")

    prompt = (
        f"Você é um assistente especialista em resumos. "
        f"Dado o texto transcrito abaixo, gere: "
        f"1) Um resumo conciso em {language_name}. "
        f"2) Lista de 3-5 pontos principais. "
        f'Responda SOMENTE em JSON válido no formato: {{"summary": "...", "key_points": ["...", "..."]}}\n\n'
        f"Texto transcrito:\n{truncated}"
    )

    try:
        from mistralai import Mistral

        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model=MISTRAL_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        content = response.choices[0].message.content
        logger.info(f"Mistral summarization complete | model={MISTRAL_MODEL}")
        return _parse_ai_response(content)

    except Exception as e:
        logger.error(f"Mistral summarization failed: {e}")
        return _fallback_summary(transcript)
