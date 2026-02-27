"""Tokenizer: normalize and validate raw input text before pattern matching.

The tokenizer's job is to give pattern matchers a clean, consistent string.
It does NOT parse — it only normalizes.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Word-to-digit tables (private to this module — only the tokenizer needs them)
# ---------------------------------------------------------------------------

# Ones and teens: zero–nineteen
_ONES: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
# Tens: twenty–fifty (cron tops out at 59 for minutes)
_TENS: dict[str, int] = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}
# Valid suffix after a tens word: one–nine only (e.g. "twenty-five", not "twenty-ten")
_SMALL: dict[str, int] = {k: v for k, v in _ONES.items() if 1 <= v <= 9}

_TENS_PAT = "|".join(_TENS)
_ONES_PAT = "|".join(_ONES)
_SMALL_PAT = "|".join(_SMALL)

# Matches compound word-numbers ("twenty-five", "thirty one") and simple
# ones/teens ("fifteen", "seven").  Compound form: tens word followed
# optionally by a hyphen or space and a ones-digit word (1–9).
_WORD_NUMBER_RE = re.compile(
    rf"\b({_TENS_PAT})(?:[- ]({_SMALL_PAT}))?\b"
    rf"|\b({_ONES_PAT})\b"
)

# Patterns that signal an unparseable or invalid request before we even try
_INEXPRESSIBLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bbiweekly\b|\bevery other week\b"),
        "Biweekly schedules cannot be expressed in standard 5-field cron",
    ),
    (
        # "bimonthly" is ambiguous (twice a month OR every two months) so we
        # reject it; use "every other month" or "twice a month" explicitly.
        re.compile(r"\bbimonthly\b"),
        "Bimonthly is ambiguous; use 'every other month' or 'twice a month' instead",
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
    if m.group(1):  # tens word matched (e.g. "twenty", "thirty")
        value = _TENS[m.group(1)]
        if m.group(2):  # optional ones suffix (e.g. "five" in "twenty-five")
            value += _SMALL[m.group(2)]
        return str(value)
    return str(_ONES[m.group(3)])  # ones/teen word matched (e.g. "fifteen")
