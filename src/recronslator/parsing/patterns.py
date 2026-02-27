"""Entry point for natural-language-to-ScheduleIntent parsing.

Imports all pattern modules (side-effect: registers patterns onto the shared
registry) and exposes the public ``parse()`` function with validation.
"""

from __future__ import annotations

import re

from recronslator.model import ScheduleIntent
from recronslator.parsing.registry import registry

# Side-effect imports: each module registers its patterns on ``registry``
import recronslator.parsing.time_patterns  # noqa: F401
import recronslator.parsing.shorthands  # noqa: F401
import recronslator.parsing.day_month_patterns  # noqa: F401


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(text: str) -> ScheduleIntent:
    """Parse a normalized text string into a ScheduleIntent.

    Raises ValueError if no pattern matches or if an inexpressible schedule
    is detected.
    """
    intent = registry.parse(text)

    _check_invalid_hours(text)
    _check_invalid_days(text)
    _check_empty(intent, text)

    return intent


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_invalid_hours(text: str) -> None:
    """Raise ValueError for times like '25:00' or '13pm'."""
    m = re.search(r"\b(2[4-9]|[3-9]\d):\d{2}", text)
    if m:
        raise ValueError(
            f"Hour {m.group().split(':')[0]} is out of range (0-23)"
        )
    m = re.search(r"\b(1[3-9]|2[0-3])\s*(?:pm?)\b", text)
    if m:
        raise ValueError(
            f"Hour {m.group(1)}pm is ambiguous/invalid; use 24-hour notation or valid 12-hour time"
        )


def _check_invalid_days(text: str) -> None:
    """Raise ValueError for day references like 'day 32'."""
    m = re.search(r"\bday\s+(3[2-9]|[4-9]\d|\d{3,})\b", text)
    if m:
        raise ValueError(
            f"Day {m.group(1)} is out of range (1-31)"
        )
    m = re.search(r"\b(3[2-9]|[4-9]\d|\d{3,})(?:st|nd|rd|th)\b", text)
    if m:
        raise ValueError(
            f"Day {m.group(1)} is out of range (1-31)"
        )


def _check_empty(intent: ScheduleIntent, raw: str) -> None:
    """Raise ValueError if the parsed intent has no meaningful content."""
    has_anything = any([
        intent.minutes is not None,
        intent.hours is not None,
        intent.minute_interval is not None,
        intent.hour_interval is not None,
        intent.hour_range is not None,
        intent.minute_range is not None,
        intent.days_of_month is not None,
        intent.day_interval is not None,
        intent.last_day_of_month,
        intent.ordinal_weekday is not None,
        intent.days_of_week is not None,
        intent.weekday_only,
        intent.weekend_only,
        intent.months is not None,
        intent.month_interval is not None,
        intent.excluded_days_of_month is not None,
        intent.excluded_days_of_week is not None,
        intent.last_weekday_of_month is not None,
    ])
    if not has_anything:
        raise ValueError(
            f"Could not understand schedule: {raw!r}. "
            "Try phrases like 'every Monday at 3am' or 'every 15 minutes'."
        )
