"""Tokenizer: normalize and validate raw input text before pattern matching.

The tokenizer's job is to give pattern matchers a clean, consistent string.
It does NOT parse — it only normalizes.
"""

from __future__ import annotations

import re

from recronslator.parsing.constants import NUMBERS, ORDINALS


# Ordinal suffixes that should NOT be replaced (they are part of ordinal words
# handled separately, e.g. "1st", "2nd", "3rd").
_ORDINAL_DIGIT_RE = re.compile(r"\b(\d+)(st|nd|rd|th)\b")

# Matches a word-number followed optionally by a hyphen+word (e.g. "forty-five")
_WORD_NUMBER_RE = re.compile(
    r"\b(forty-five|twenty|thirty|forty|fifty|"
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen)\b"
)

# Patterns that signal an unparseable or invalid request before we even try
_INEXPRESSIBLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bbiweekly\b|\bevery other week\b"),
        "Biweekly schedules cannot be expressed in standard 5-field cron",
    ),
    (
        re.compile(r"\bbimonthly\b|\bevery other month\b"),
        "Bimonthly schedules cannot be expressed in standard 5-field cron",
    ),
]


def tokenize(text: str) -> str:
    """Normalize a natural language schedule description.

    Returns a cleaned, lowercase string ready for pattern matching.

    Raises ValueError for:
    - empty or whitespace-only input
    - multi-line input
    - inputs containing inexpressible schedule concepts (biweekly, etc.)
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Schedule description cannot be empty")

    if "\n" in text or "\r" in text:
        raise ValueError(
            "Schedule description must be a single line; "
            "got multi-line input"
        )

    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)

    # Check for structurally inexpressible patterns early
    for pattern, message in _INEXPRESSIBLE_PATTERNS:
        if pattern.search(normalized):
            raise ValueError(message)

    # Expand word-numbers to digits (e.g. "fifteen" → "15")
    normalized = _WORD_NUMBER_RE.sub(_replace_word_number, normalized)

    # Preserve ordinal digit tokens (e.g. "1st", "3rd") — keep them as-is so
    # patterns can match them directly.

    return normalized


def _replace_word_number(m: re.Match[str]) -> str:
    word = m.group(1)
    # Check NUMBERS first, then ORDINALS as fallback
    if word in NUMBERS:
        return str(NUMBERS[word])
    if word in ORDINALS:
        return str(ORDINALS[word])
    return word
