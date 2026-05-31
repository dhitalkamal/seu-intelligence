"""Multilingual NLP tokenizer supporting English and Nepali (Devanagari)."""

from __future__ import annotations

import re

# Devanagari Unicode block: U+0900 to U+097F
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Nepali punctuation to strip from tokens
_NEPALI_PUNCT = re.compile(r"[।॥,!?\"'()\[\]{}<>]")

# English stop words to exclude from results (short tokens covered by len check)
_EN_STOP_WORDS = frozenset({"the", "and", "for", "are", "was", "were", "but", "not"})


def _detect_language(text: str) -> str:
    """Return 'ne' if text contains Devanagari characters, else 'en'."""
    return "ne" if _DEVANAGARI_RE.search(text) else "en"


def _tokenize_english(text: str) -> list[str]:
    """Split English text and return tokens longer than 2 chars, excluding stop words."""
    tokens = text.split()
    return [t for t in tokens if len(t) > 2 and t.lower() not in _EN_STOP_WORDS]


def _tokenize_nepali(text: str) -> list[str]:
    """Split Nepali text on whitespace and strip Devanagari punctuation."""
    tokens = text.split()
    cleaned: list[str] = []
    for token in tokens:
        token = _NEPALI_PUNCT.sub("", token).strip()
        if token:
            cleaned.append(token)
    return cleaned


def tokenize_query(query: str) -> dict:
    """
    Tokenize a search query in English or Nepali.

    Returns a dict with:
      - keywords: list of meaningful tokens
      - language: 'en' or 'ne'
      - filters: dict reserved for future structured filter extraction
    """
    if not query.strip():
        return {"keywords": [], "language": "en", "filters": {}}

    language = _detect_language(query)
    if language == "ne":
        keywords = _tokenize_nepali(query)
    else:
        keywords = _tokenize_english(query)

    return {"keywords": keywords, "language": language, "filters": {}}
