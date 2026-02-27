"""Shared parsing helpers used by multiple pattern modules."""

from __future__ import annotations

import re

from recronslator.parsing.constants import SPECIAL_TIMES


def parse_hour(token: str) -> int:
    """Parse a time token like '3am', '3a', '14', '2pm', '2p', '12pm' -> 24h integer."""
    token = token.strip()
    if token in SPECIAL_TIMES:
        return SPECIAL_TIMES[token][0]
    if token.endswith("am"):
        h = int(token[:-2])
        return 0 if h == 12 else h
    if token.endswith("a"):
        h = int(token[:-1])
        return 0 if h == 12 else h
    if token.endswith("pm"):
        h = int(token[:-2])
        return h if h == 12 else h + 12
    if token.endswith("p"):
        h = int(token[:-1])
        return h if h == 12 else h + 12
    return int(token)


def parse_time_token(token: str) -> tuple[int, int]:
    """Parse 'H:MM am/pm' or 'Ham/pm' -> (hour24, minute)."""
    token = token.strip()
    if token in SPECIAL_TIMES:
        return SPECIAL_TIMES[token]

    m = re.match(r"^(\d{1,2}):(\d{2})\s*(am?|pm?)?$", token)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        meridiem = m.group(3)
        if meridiem in ("pm", "p") and h != 12:
            h += 12
        elif meridiem in ("am", "a") and h == 12:
            h = 0
        return h, mn

    h = parse_hour(token)
    return h, 0


def parse_time_range(text: str) -> tuple[int, int] | None:
    """Extract (start_hour, end_hour) from 'between Xam and Ypm' or 'from Xam to Ypm'."""
    m = re.search(
        r"between\s+(\d{1,2}(?::\d{2})?\s*(?:am?|pm?)?)\s+and\s+"
        r"(\d{1,2}(?::\d{2})?\s*(?:am?|pm?)?)",
        text,
    )
    if not m:
        m = re.search(
            r"from\s+(\d{1,2}(?::\d{2})?\s*(?:am?|pm?)?)\s+to\s+"
            r"(\d{1,2}(?::\d{2})?\s*(?:am?|pm?)?)",
            text,
        )
    if not m:
        return None
    start_h, _ = parse_time_token(m.group(1).strip())
    end_h, _ = parse_time_token(m.group(2).strip())
    return start_h, end_h


def parse_multiple_times(text: str) -> list[tuple[int, int]]:
    """Extract a list of (hour, minute) from text containing multiple times."""
    pattern = re.compile(
        r"(\d{1,2}(?::\d{2})?\s*(?:am?|pm?)?)"
        r"(?:\s*,\s*|\s+and\s+|\s*$"
        r"|\s+(?:on|in|at|of|during|every|from|to|until|before|after|except)\b)"
    )
    tokens = pattern.findall(text)
    if not tokens:
        return []

    results: list[tuple[int, int]] = []
    last_meridiem: str | None = None

    for raw in tokens:
        raw = raw.strip()
        if not raw:
            continue
        has_am = "am" in raw or raw.endswith("a")
        has_pm = "pm" in raw or raw.endswith("p")
        if has_am or has_pm:
            last_meridiem = "pm" if has_pm else "am"
        h, mn = parse_time_token(raw)
        if not has_am and not has_pm and last_meridiem == "pm":
            if h < 12:
                h += 12
        results.append((h, mn))

    return results
