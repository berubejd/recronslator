"""Pattern registry and all natural-language-to-ScheduleIntent patterns.

Architecture: hybrid composite/additive
- Composite patterns (100s, 200s) own the full phrase and return a complete intent.
- Additive enrichers (300s–600s) layer time/day/month onto a partial intent.

The registry's parse() method:
1. Tries composite patterns first. First match wins and sets the base intent.
2. Runs additive enrichers in order to layer additional fields.
3. If the intent is still empty after all passes, raises ValueError.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from recronslator.model import ScheduleIntent
from recronslator.parsing.constants import (
    BUSINESS_HOURS,
    MONTH_NAMES,
    ORDINALS,
    QUARTER_MONTHS,
    SPECIAL_TIMES,
    WEEKDAYS,
)


# ---------------------------------------------------------------------------
# Registry infrastructure
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    name: str
    priority: int
    match: Callable[[str], ScheduleIntent | None]
    is_composite: bool = True  # False = additive enricher


class PatternRegistry:
    def __init__(self) -> None:
        self._patterns: list[Pattern] = []

    def register(
        self,
        name: str,
        priority: int,
        *,
        composite: bool = True,
    ) -> Callable[[Callable[[str], ScheduleIntent | None]], Callable[[str], ScheduleIntent | None]]:
        """Decorator to register a pattern function."""
        def decorator(
            fn: Callable[[str], ScheduleIntent | None]
        ) -> Callable[[str], ScheduleIntent | None]:
            self._patterns.append(
                Pattern(name=name, priority=priority, match=fn, is_composite=composite)
            )
            self._patterns.sort(key=lambda p: p.priority)
            return fn
        return decorator

    def parse(self, text: str) -> ScheduleIntent:
        """Try all patterns and return a populated ScheduleIntent.

        Step 1: Try composite patterns in priority order. The first match
                wins and provides the base intent.
        Step 2: Run additive enrichers in priority order, mutating the intent
                in place.
        Step 3: If the intent has no meaningful content, raise ValueError.
        """
        composites = [p for p in self._patterns if p.is_composite]
        enrichers = [p for p in self._patterns if not p.is_composite]

        intent: ScheduleIntent | None = None

        for pattern in composites:
            result = pattern.match(text)
            if result is not None:
                intent = result
                break

        if intent is None:
            intent = ScheduleIntent()

        for enricher in enrichers:
            result = enricher.match(text)
            if result is not None:
                _merge_intent(intent, result)

        return intent


def _merge_intent(base: ScheduleIntent, addition: ScheduleIntent) -> None:
    """Merge non-None fields from addition into base (additive enrichment)."""
    for field_name in addition.__dataclass_fields__:
        val = getattr(addition, field_name)
        if val is None or val is False:
            continue
        existing = getattr(base, field_name)
        if existing is None or existing is False:
            setattr(base, field_name, val)


# ---------------------------------------------------------------------------
# Module-level registry instance
# ---------------------------------------------------------------------------

registry = PatternRegistry()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _parse_hour(token: str) -> int:
    """Parse a time token like '3am', '14', '2pm', '12pm' → 24h integer."""
    token = token.strip()
    if token in SPECIAL_TIMES:
        return SPECIAL_TIMES[token][0]
    if token.endswith("am"):
        h = int(token[:-2])
        return 0 if h == 12 else h
    if token.endswith("pm"):
        h = int(token[:-2])
        return h if h == 12 else h + 12
    return int(token)


def _parse_time_token(token: str) -> tuple[int, int]:
    """Parse 'H:MM am/pm' or 'Ham/pm' → (hour24, minute)."""
    token = token.strip()
    if token in SPECIAL_TIMES:
        return SPECIAL_TIMES[token]

    # e.g. "4:30pm", "4:30 pm"
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)?$", token)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        meridiem = m.group(3)
        if meridiem == "pm" and h != 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        return h, mn

    # e.g. "3am", "14"
    h = _parse_hour(token)
    return h, 0


def _parse_time_range(text: str) -> tuple[int, int] | None:
    """Extract (start_hour, end_hour) from 'between Xam and Ypm' style."""
    m = re.search(
        r"between\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+and\s+"
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
        text,
    )
    if not m:
        return None
    start_h, _ = _parse_time_token(m.group(1).strip())
    end_h, _ = _parse_time_token(m.group(2).strip())
    return start_h, end_h


def _parse_multiple_times(text: str) -> list[tuple[int, int]]:
    """Extract a list of (hour, minute) from text containing multiple times."""
    # Match patterns like "9am, 1pm and 5pm" or "6:30 and 18:30"
    pattern = re.compile(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)"
        r"(?:\s*,\s*|\s+and\s+|\s*$)"
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
        if "am" in raw or "pm" in raw:
            last_meridiem = "pm" if "pm" in raw else "am"
        h, mn = _parse_time_token(raw)
        # Propagate meridiem context forward when it's ambiguous
        if "am" not in raw and "pm" not in raw and last_meridiem == "pm":
            if h < 12:
                h += 12
        results.append((h, mn))

    return results


# ---------------------------------------------------------------------------
# Priority 100 — Interval patterns (composite)
# ---------------------------------------------------------------------------

@registry.register("minute_interval_ranged", priority=100)
def _p_minute_interval_ranged(text: str) -> ScheduleIntent | None:
    """every N minutes between Xam and Ypm [on weekdays]"""
    m = re.search(r"every\s+(\d+)\s+minutes?.*between", text)
    if not m:
        return None
    interval = int(m.group(1))
    if interval > 59:
        raise ValueError(f"Minute interval {interval} is out of range (1-59)")
    hr = _parse_time_range(text)
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(
        minute_interval=interval,
        hour_range=hr,
        weekday_only=weekday_only,
    )


@registry.register("minute_interval", priority=101)
def _p_minute_interval(text: str) -> ScheduleIntent | None:
    """every N minutes (no time range)"""
    if "between" in text:
        return None
    if "business hours" in text:
        return None
    m = re.search(r"every\s+(\d+)\s+minutes?", text)
    if not m:
        return None
    interval = int(m.group(1))
    if interval > 59:
        raise ValueError(f"Minute interval {interval} is out of range (1-59)")
    return ScheduleIntent(minute_interval=interval)


@registry.register("hour_interval", priority=110)
def _p_hour_interval(text: str) -> ScheduleIntent | None:
    """every N hours (not 'every hour' — that's shorthand_hourly)"""
    m = re.search(r"every\s+(\d+)\s+hours?", text)
    if not m:
        return None
    interval = int(m.group(1))
    if interval == 1:
        # "every 1 hour" → same as "every hour" → minutes=[0]
        return ScheduleIntent(minutes=[0])
    if interval > 23:
        raise ValueError(f"Hour interval {interval} is out of range (1-23)")
    return ScheduleIntent(hour_interval=interval)


@registry.register("business_hours_interval", priority=120)
def _p_business_hours_interval(text: str) -> ScheduleIntent | None:
    """every N minutes during business hours"""
    if "business hours" not in text:
        return None
    m = re.search(r"every\s+(\d+)\s+minutes?", text)
    if not m:
        return None
    interval = int(m.group(1))
    return ScheduleIntent(
        minute_interval=interval,
        hour_range=BUSINESS_HOURS,
        weekday_only=True,
    )


# ---------------------------------------------------------------------------
# Priority 200 — Special shorthand (composite)
# ---------------------------------------------------------------------------

@registry.register("shorthand_hourly", priority=200)
def _p_shorthand_hourly(text: str) -> ScheduleIntent | None:
    """hourly / every hour"""
    if re.search(r"\bhourly\b", text) or re.search(r"\bevery\s+hour\b", text):
        # "every hour on the half hour" is handled by half_hour (priority 210)
        if "half hour" in text or "half past" in text:
            return None
        if "quarter past" in text:
            return None
        return ScheduleIntent(minutes=[0])
    return None


@registry.register("twice_daily", priority=203)
def _p_twice_daily(text: str) -> ScheduleIntent | None:
    """twice daily at H:MM and H:MM"""
    if "twice daily" not in text and "twice a day" not in text:
        return None
    m = re.search(
        r"at\s+([\d:]+\s*(?:am|pm)?)\s+and\s+([\d:]+\s*(?:am|pm)?)",
        text,
    )
    if not m:
        return None
    t1 = _parse_time_token(m.group(1).strip())
    t2 = _parse_time_token(m.group(2).strip())
    hours = sorted({t1[0], t2[0]})
    minutes_set = {t1[1], t2[1]}
    mn = list(minutes_set)[0] if len(minutes_set) == 1 else 0
    return ScheduleIntent(minutes=[mn], hours=hours)


def _text_has_explicit_time(text: str) -> bool:
    """Return True if the text contains an explicit time specification."""
    # H:MM with optional am/pm
    if re.search(r"\d{1,2}:\d{2}", text):
        return True
    # bare Xam / Xpm
    if re.search(r"\d{1,2}\s*(?:am|pm)\b", text):
        return True
    # special time names
    for name in SPECIAL_TIMES:
        if re.search(r"\b" + name + r"\b", text):
            return True
    return False


@registry.register("shorthand_daily", priority=205)
def _p_shorthand_daily(text: str) -> ScheduleIntent | None:
    """daily / every day — defaults to midnight; time enrichers override if time is present"""
    if "twice" in text:
        return None
    if not (re.search(r"\bdaily\b", text) or re.search(r"\bevery\s+day\b", text)):
        return None
    # If an explicit time is given, don't pre-fill; let enrichers set it
    if _text_has_explicit_time(text):
        return ScheduleIntent()
    return ScheduleIntent(minutes=[0], hours=[0])


@registry.register("shorthand_weekly", priority=202)
def _p_shorthand_weekly(text: str) -> ScheduleIntent | None:
    """weekly on <day>"""
    m = re.search(r"\bweekly\b", text)
    if not m:
        return None
    # Extract specific day if present
    for day_name, day_num in WEEKDAYS.items():
        if re.search(r"\b" + day_name + r"\b", text):
            return ScheduleIntent(minutes=[0], hours=[0], days_of_week=[day_num])
    return ScheduleIntent(minutes=[0], hours=[0])


@registry.register("half_hour", priority=210)
def _p_half_hour(text: str) -> ScheduleIntent | None:
    """every hour on the half hour"""
    if "half hour" in text or "half past" in text:
        return ScheduleIntent(minutes=[30])
    return None


@registry.register("quarter_hour", priority=211)
def _p_quarter_hour(text: str) -> ScheduleIntent | None:
    """every quarter hour [between X and Y]"""
    if not re.search(r"\bquarter\s+hour\b", text):
        return None
    hr = _parse_time_range(text)
    return ScheduleIntent(minute_interval=15, hour_range=hr)


@registry.register("quarter_past", priority=212)
def _p_quarter_past(text: str) -> ScheduleIntent | None:
    """(weekdays) at quarter past each hour"""
    if "quarter past" not in text:
        return None
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(minutes=[15], weekday_only=weekday_only)


# ---------------------------------------------------------------------------
# Priority 300 — Specific time enrichers (additive)
# ---------------------------------------------------------------------------

@registry.register("specific_time_with_minutes", priority=301, composite=False)
def _e_specific_time_with_minutes(text: str) -> ScheduleIntent | None:
    """at H:MM [am/pm] — only for times with explicit minutes (colon format)"""
    m = re.search(
        r"\bat\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)",
        text,
    )
    if not m:
        m = re.search(r"(\d{1,2}:\d{2}\s*(?:am|pm)?)", text)
        if not m:
            return None
    h, mn = _parse_time_token(m.group(1).strip())
    return ScheduleIntent(minutes=[mn], hours=[h])


@registry.register("single_bare_time", priority=303, composite=False)
def _e_single_bare_time(text: str) -> ScheduleIntent | None:
    """at Xam / at Xpm — bare hour with am/pm marker, no colon"""
    # Must have explicit am/pm marker; pure numbers are too ambiguous
    m = re.search(r"\bat\s+(\d{1,2})\s*(am|pm)\b", text)
    if not m:
        return None
    token = m.group(1) + m.group(2)
    h, mn = _parse_time_token(token)
    return ScheduleIntent(minutes=[mn], hours=[h])


@registry.register("times_per_hour", priority=299, composite=False)
def _e_times_per_hour_early(text: str) -> ScheduleIntent | None:
    """N times per hour at M1, M2, and M3 minutes — high priority composite enricher"""
    if "per hour" not in text and "times per hour" not in text:
        return None
    m = re.search(r"\bat\s+([\d,\s]+(?:and\s+\d+)?)\s+minutes?", text)
    if not m:
        return None
    raw = m.group(1)
    nums = [int(x) for x in re.findall(r"\d+", raw)]
    if not nums:
        return None
    return ScheduleIntent(minutes=sorted(nums))


@registry.register("specific_times", priority=300, composite=False)
def _e_specific_times(text: str) -> ScheduleIntent | None:
    """at Xam, Ypm and Zpm  (multiple times, whole hours only)"""
    # Don't match when this is a "times per hour" pattern
    if "per hour" in text:
        return None
    # Only trigger when we see "at" followed by multiple hour tokens
    m = re.search(
        r"\bat\s+((?:\d{1,2}\s*(?:am|pm)?"
        r"(?:\s*,\s*|\s+and\s+))+\d{1,2}\s*(?:am|pm)?)",
        text,
    )
    if not m:
        return None

    raw_list = m.group(1)
    # Check for H:MM pattern — let specific_time_with_minutes handle those
    if ":" in raw_list:
        return None

    times = _parse_multiple_times(raw_list)
    if len(times) < 2:
        return None
    hours = sorted({h for h, _ in times})
    minutes = sorted({mn for _, mn in times})
    mn = minutes[0] if len(set(minutes)) == 1 else 0
    return ScheduleIntent(minutes=[mn], hours=hours)


@registry.register("special_time_name", priority=302, composite=False)
def _e_special_time_name(text: str) -> ScheduleIntent | None:
    """at midnight / at noon / at dawn"""
    for name, (h, mn) in SPECIAL_TIMES.items():
        if re.search(r"\b" + name + r"\b", text):
            return ScheduleIntent(minutes=[mn], hours=[h])
    return None






@registry.register("first_n_minutes", priority=330, composite=False)
def _e_first_n_minutes(text: str) -> ScheduleIntent | None:
    """once per hour in the first N minutes"""
    m = re.search(r"(?:once per hour\s+)?in the first\s+(\d+)\s+minutes?", text)
    if not m:
        return None
    n = int(m.group(1)) - 1  # "first 15 minutes" → 0-14
    return ScheduleIntent(minute_range=(0, n))


# ---------------------------------------------------------------------------
# Priority 400 — Day-of-week enrichers (additive)
# ---------------------------------------------------------------------------

@registry.register("weekday_constraint", priority=400, composite=False)
def _e_weekday_constraint(text: str) -> ScheduleIntent | None:
    if re.search(r"\bweekdays?\b", text):
        return ScheduleIntent(weekday_only=True)
    return None


@registry.register("workday_constraint", priority=401, composite=False)
def _e_workday_constraint(text: str) -> ScheduleIntent | None:
    if re.search(r"\bworkdays?\b", text) and "except" not in text:
        return ScheduleIntent(weekday_only=True)
    return None


@registry.register("weekend_constraint", priority=402, composite=False)
def _e_weekend_constraint(text: str) -> ScheduleIntent | None:
    if re.search(r"\bweekends?\b", text):
        return ScheduleIntent(weekend_only=True)
    return None


@registry.register("named_days", priority=410, composite=False)
def _e_named_days(text: str) -> ScheduleIntent | None:
    """on Monday, Tuesdays and Fridays (handles plural forms)"""
    days: list[int] = []
    # Use the short names (3-letter) to avoid matching abbreviations inside longer words
    # Match plural forms too: mondays, tuesdays, etc.
    for day_name, day_num in WEEKDAYS.items():
        if re.search(r"\b" + day_name + r"s?\b", text):
            days.append(day_num)
    if not days:
        return None
    return ScheduleIntent(days_of_week=sorted(set(days)))


# ---------------------------------------------------------------------------
# Priority 500 — Day-of-month enrichers (additive)
# ---------------------------------------------------------------------------

@registry.register("ordinal_weekday", priority=500, composite=False)
def _e_ordinal_weekday(text: str) -> ScheduleIntent | None:
    """first/second/... Monday of every month"""
    m = re.search(
        r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)"
        r"\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        text,
    )
    if not m:
        return None
    nth = ORDINALS[m.group(1)]
    weekday = WEEKDAYS[m.group(2)]
    return ScheduleIntent(ordinal_weekday=(nth, weekday))


@registry.register("last_day", priority=510, composite=False)
def _e_last_day(text: str) -> ScheduleIntent | None:
    if re.search(r"\blast\s+day\b", text):
        return ScheduleIntent(last_day_of_month=True)
    return None


@registry.register("specific_day_of_month", priority=520, composite=False)
def _e_specific_day_of_month(text: str) -> ScheduleIntent | None:
    """on the Nth (of the month) / monthly on the Nth"""
    # Match ordinal-style day reference: "3rd day", "on the 15th", "monthly on the 15th"
    m = re.search(
        r"(?:on\s+the\s+|monthly\s+on\s+the\s+|on\s+day\s+)?(\d+)(?:st|nd|rd|th)(?!\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
        text,
    )
    if not m:
        return None
    day = int(m.group(1))
    if not 1 <= day <= 31:
        raise ValueError(f"Day-of-month value {day} is out of range (1-31)")
    return ScheduleIntent(days_of_month=[day])


@registry.register("day_interval", priority=530, composite=False)
def _e_day_interval(text: str) -> ScheduleIntent | None:
    """every 4th day / every N days / every fourth day"""
    # Digit ordinal: "every 4th day", "every 4 days"
    m = re.search(r"every\s+(\d+)(?:st|nd|rd|th)?\s+days?", text)
    if m:
        n = int(m.group(1))
        if not 1 <= n <= 31:
            raise ValueError(f"Day interval {n} is out of range (1-31)")
        return ScheduleIntent(day_interval=n)
    # Word ordinal: "every fourth day", "every third day"
    ordinal_pattern = "|".join(ORDINALS.keys())
    m2 = re.search(r"every\s+(" + ordinal_pattern + r")\s+days?", text)
    if m2:
        n = ORDINALS[m2.group(1)]
        if not 1 <= n <= 31:
            raise ValueError(f"Day interval {n} is out of range (1-31)")
        return ScheduleIntent(day_interval=n)
    return None


@registry.register("first_day", priority=540, composite=False)
def _e_first_day(text: str) -> ScheduleIntent | None:
    """first day of every month"""
    if re.search(r"\bfirst\s+day\b", text):
        return ScheduleIntent(days_of_month=[1])
    return None


@registry.register("first_n_days", priority=541, composite=False)
def _e_first_n_days(text: str) -> ScheduleIntent | None:
    """first N days of each [quarter/month]"""
    m = re.search(r"\bfirst\s+(\d+)\s+days?\b", text)
    if not m:
        return None
    n = int(m.group(1))
    return ScheduleIntent(days_of_month=list(range(1, n + 1)))


@registry.register("day_exception", priority=550, composite=False)
def _e_day_exception(text: str) -> ScheduleIntent | None:
    """workdays except the 13th"""
    if "except" not in text:
        return None
    m = re.search(r"except.*?(\d+)(?:st|nd|rd|th)", text)
    if not m:
        return None
    excluded = int(m.group(1))
    if not 1 <= excluded <= 31:
        raise ValueError(f"Excluded day {excluded} is out of range (1-31)")
    # Build day_of_month list excluding the exception
    days = [d for d in range(1, 32) if d != excluded]
    # Format as compact ranges: "1-12,14-31" for excluding 13
    dom_str = _days_to_dom_string(days)
    # Store as excluded_days; compiler will handle rendering
    return ScheduleIntent(
        excluded_days_of_month=[excluded],
        weekday_only=True,
    )


def _days_to_dom_string(days: list[int]) -> str:
    """Convert a list of day ints to a compact range string like '1-12,14-31'."""
    if not days:
        return ""
    parts: list[str] = []
    start = days[0]
    prev = days[0]
    for d in days[1:]:
        if d == prev + 1:
            prev = d
        else:
            parts.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = d
    parts.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ",".join(parts)


# ---------------------------------------------------------------------------
# Priority 600 — Month enrichers (additive)
# ---------------------------------------------------------------------------

@registry.register("quarter_months", priority=600, composite=False)
def _e_quarter_months(text: str) -> ScheduleIntent | None:
    """each quarter / every quarter (not 'quarter hour' or 'quarter past')"""
    if re.search(r"\b(?:each|every)\s+quarter\b(?!\s+(?:hour|past))", text):
        return ScheduleIntent(months=QUARTER_MONTHS)
    return None


@registry.register("named_months", priority=610, composite=False)
def _e_named_months(text: str) -> ScheduleIntent | None:
    """in January / every March"""
    months: list[int] = []
    for name, num in MONTH_NAMES.items():
        if re.search(r"\b" + name + r"\b", text):
            months.append(num)
    if not months:
        return None
    return ScheduleIntent(months=sorted(set(months)))


# ---------------------------------------------------------------------------
# Validation helpers used by the public parse() call
# ---------------------------------------------------------------------------

def parse(text: str) -> ScheduleIntent:
    """Entry point: parse a normalized text string into a ScheduleIntent.

    Raises ValueError if no pattern matches or if an inexpressible schedule
    is detected.
    """
    intent = registry.parse(text)

    # Post-parse validity checks
    _check_invalid_hours(text)
    _check_invalid_days(text)
    _check_empty(intent, text)

    return intent


def _check_invalid_hours(text: str) -> None:
    """Raise ValueError for times like '25:00' or '13pm'."""
    # e.g. "at 25:00"
    m = re.search(r"\b(2[4-9]|[3-9]\d):\d{2}", text)
    if m:
        raise ValueError(
            f"Hour {m.group().split(':')[0]} is out of range (0-23)"
        )
    # e.g. "at 13pm" (13 + 12 would be 25)
    m = re.search(r"\b(1[3-9]|2[0-3])\s*pm\b", text)
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
    # ordinal > 31
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
        intent.excluded_days_of_month is not None,
    ])
    if not has_anything:
        raise ValueError(
            f"Could not understand schedule: {raw!r}. "
            "Try phrases like 'every Monday at 3am' or 'every 15 minutes'."
        )
