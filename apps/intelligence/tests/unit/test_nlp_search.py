"""Unit tests for the NLP tokenizer - English and Nepali."""

from __future__ import annotations

from apps.intelligence.application.use_cases.tokenize import tokenize_query


def test_english_basic_tokenization():
    """English query returns tokens longer than 2 chars."""
    result = tokenize_query("show me events in Kathmandu")
    assert "show" in result["keywords"]
    assert "events" in result["keywords"]
    assert "Kathmandu" in result["keywords"]
    # short stop words removed
    assert "me" not in result["keywords"]
    assert "in" not in result["keywords"]


def test_english_language_detected():
    """English text sets language to 'en'."""
    result = tokenize_query("music concert festival")
    assert result["language"] == "en"


def test_nepali_basic_tokenization():
    """Nepali Devanagari query is split on whitespace."""
    result = tokenize_query("काठमाडौं मा संगीत कार्यक्रम")
    assert "काठमाडौं" in result["keywords"]
    assert "संगीत" in result["keywords"]
    assert "कार्यक्रम" in result["keywords"]


def test_nepali_language_detected():
    """Devanagari text sets language to 'ne'."""
    result = tokenize_query("काठमाडौं मा कार्यक्रम")
    assert result["language"] == "ne"


def test_nepali_punctuation_stripped():
    """Nepali full stop (।) is stripped from tokens."""
    result = tokenize_query("संगीत कार्यक्रम।")
    for kw in result["keywords"]:
        assert "।" not in kw


def test_empty_query_returns_empty():
    """Empty query returns no keywords."""
    result = tokenize_query("")
    assert result["keywords"] == []


def test_mixed_script_falls_back_to_nepali():
    """Query containing any Devanagari characters is treated as Nepali."""
    result = tokenize_query("event काठमाडौं")
    assert result["language"] == "ne"


def test_english_case_preserved():
    """English token casing is preserved."""
    result = tokenize_query("Kathmandu Festival")
    assert "Kathmandu" in result["keywords"]
    assert "Festival" in result["keywords"]
