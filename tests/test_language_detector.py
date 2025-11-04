"""Tests for language detection."""

import pytest
from app.utils.language_detector import detect_language, validate_language


def test_detect_chinese():
    """Test Chinese character detection."""
    assert detect_language("苹果手机") == "zh"
    assert detect_language("Nike 跑步鞋") == "zh"


def test_detect_japanese():
    """Test Japanese character detection."""
    assert detect_language("アップル") == "ja"
    assert detect_language("こんにちは") == "ja"


def test_detect_korean():
    """Test Korean character detection."""
    assert detect_language("삼성 갤럭시") == "ko"


def test_detect_english():
    """Test English detection."""
    assert detect_language("Nike shoes") == "en"
    assert detect_language("Apple iPhone") == "en"


def test_detect_spanish():
    """Test Spanish detection."""
    lang = detect_language("zapatos deportivos")
    assert lang in ["es", "en"]  # May vary based on langdetect


def test_validate_language_with_valid_code():
    """Test validation with valid language code."""
    assert validate_language("zh", "some text") == "zh"
    assert validate_language("en", "some text") == "en"


def test_validate_language_with_none():
    """Test validation with None (auto-detect)."""
    assert validate_language(None, "苹果手机") == "zh"
    assert validate_language(None, "Nike shoes") == "en"


def test_validate_language_with_invalid_code():
    """Test validation with invalid code falls back to auto-detect."""
    assert validate_language("invalid", "Nike shoes") == "en"
