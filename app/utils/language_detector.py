"""Language detection utility."""

import re
from langdetect import detect, LangDetectException
from app.core.config import settings


def detect_language(text: str) -> str:
    """
    Detect the language of the input text.

    Args:
        text: Input text to detect language

    Returns:
        Language code (zh, en, es, id, pt, fr, ja, ru, de, ko) or 'en' as fallback
    """

    # Use langdetect for other languages
    try:
        detected = detect(text)
        # Map langdetect codes to our supported codes
        lang_map = {
            "zh-cn": "zh",
            "zh-tw": "zh",
            "ja": "ja",
            "ko": "ko",
            "en": "en",
            "es": "es",
            "id": "id",
            "pt": "pt",
            "fr": "fr",
            "ru": "ru",
            "de": "de",
        }
        return lang_map.get(detected, "en")
    except LangDetectException:
        return "en"  # Default fallback


def validate_language(lang: str | None, text: str) -> str:
    """
    Validate and return language code.

    Args:
        lang: Provided language code or None
        text: Text to detect language from if lang is None

    Returns:
        Valid language code
    """
    if lang and lang in settings.supported_languages:
        return lang
    return detect_language(text)
