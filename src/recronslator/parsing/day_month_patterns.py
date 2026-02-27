"""Day-of-week, day-of-month, and month enrichers.

All patterns here are additive enrichers (``composite=False``).  They layer
day and month constraints onto whatever time shape a composite has already
established.
"""

from __future__ import annotations

import re

from recronslator.model import ScheduleIntent
from recronslator.parsing.constants import (
    MONTH_NAMES,
    ORDINALS,
    QUARTER_MONTHS,
    WEEKDAYS,
)
from recronslator.parsing.registry import registry

# ---------------------------------------------------------------------------
# Day-of-week enrichers (priorities 400-410)
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
    if not re.search(r"\bweekends?\b", text):
        return None
    if re.search(r"\bexcept\s+weekends?\b", text):
        return ScheduleIntent(weekday_only=True)
    return ScheduleIntent(weekend_only=True)


@registry.register("dow_exception", priority=403, composite=False)
def _e_dow_exception(text: str) -> ScheduleIntent | None:
    """every day except monday -- exclude a specific weekday."""
    if "except" not in text:
        return None
    day_pattern = "|".join(WEEKDAYS.keys())
    m = re.search(r"\bexcept\s+(" + day_pattern + r")s?\b", text)
    if not m:
        return None
    excluded_day = WEEKDAYS[m.group(1)]
    return ScheduleIntent(excluded_days_of_week=[excluded_day])


@registry.register("named_day_range", priority=405, composite=False)
def _e_named_day_range(text: str) -> ScheduleIntent | None:
    """monday through wednesday -- fill in the full contiguous day range."""
    day_pattern = "|".join(WEEKDAYS.keys())
    m = re.search(
        r"\b(" + day_pattern + r")s?\s+(?:through|thru)\s+(" + day_pattern + r")s?\b",
        text,
    )
    if not m:
        return None
    start = WEEKDAYS[m.group(1)]
    end = WEEKDAYS[m.group(2)]
    if start <= end:
        days = list(range(start, end + 1))
    else:
        days = list(range(start, 7)) + list(range(0, end + 1))
    return ScheduleIntent(days_of_week=sorted(set(days)))


@registry.register("named_days", priority=410, composite=False)
def _e_named_days(text: str) -> ScheduleIntent | None:
    """on Monday, Tuesdays and Fridays (handles plural forms)"""
    day_pattern = "|".join(WEEKDAYS.keys())
    cleaned = re.sub(r"\bexcept\s+(?:" + day_pattern + r")s?\b", "", text)

    days: list[int] = []
    for day_name, day_num in WEEKDAYS.items():
        if re.search(r"\b" + day_name + r"s?\b", cleaned):
            days.append(day_num)
    if not days:
        return None
    return ScheduleIntent(days_of_week=sorted(set(days)))


# ---------------------------------------------------------------------------
# Day-of-month enrichers (priorities 500-550)
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


@registry.register("last_weekday", priority=508, composite=False)
def _e_last_weekday(text: str) -> ScheduleIntent | None:
    """last Friday / last Monday of the month"""
    day_pattern = "|".join(WEEKDAYS.keys())
    m = re.search(r"\blast\s+(" + day_pattern + r")\b", text)
    if not m:
        return None
    weekday = WEEKDAYS[m.group(1)]
    return ScheduleIntent(last_weekday_of_month=weekday)


@registry.register("last_day", priority=510, composite=False)
def _e_last_day(text: str) -> ScheduleIntent | None:
    if not re.search(r"\blast\s+day\b", text):
        return None
    return ScheduleIntent(last_day_of_month=True)


@registry.register("specific_day_of_month", priority=520, composite=False)
def _e_specific_day_of_month(text: str) -> ScheduleIntent | None:
    """on the Nth / on the 1st and 15th (of the month)"""
    ordinal_re = re.compile(
        r"(\d+)(?:st|nd|rd|th)(?!\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))"
    )
    days: list[int] = []
    for m in ordinal_re.finditer(text):
        day = int(m.group(1))
        if not 1 <= day <= 31:
            raise ValueError(f"Day-of-month value {day} is out of range (1-31)")
        days.append(day)
    if not days:
        return None
    return ScheduleIntent(days_of_month=sorted(set(days)))


@registry.register("day_interval", priority=530, composite=False)
def _e_day_interval(text: str) -> ScheduleIntent | None:
    """every 4th day / every N days / every other day / every fourth day"""
    if re.search(r"\bevery\s+other\s+day\b", text):
        return ScheduleIntent(day_interval=2)
    m = re.search(r"every\s+(\d+)(?:st|nd|rd|th)?\s+days?", text)
    if m:
        n = int(m.group(1))
        if not 1 <= n <= 31:
            raise ValueError(f"Day interval {n} is out of range (1-31)")
        return ScheduleIntent(day_interval=n)
    ordinal_pattern = "|".join(ORDINALS.keys())
    m2 = re.search(r"every\s+(" + ordinal_pattern + r")\s+days?", text)
    if m2:
        n = ORDINALS[m2.group(1)]
        if not 1 <= n <= 31:
            raise ValueError(f"Day interval {n} is out of range (1-31)")
        return ScheduleIntent(day_interval=n)
    return None


@registry.register("dom_range", priority=535, composite=False)
def _e_dom_range(text: str) -> ScheduleIntent | None:
    """on days N-M of the month"""
    m = re.search(r"\bon\s+days\s+(\d{1,2})-(\d{1,2})\b", text)
    if not m:
        return None
    lo, hi = int(m.group(1)), int(m.group(2))
    return ScheduleIntent(days_of_month=list(range(lo, hi + 1)))


@registry.register("first_day", priority=540, composite=False)
def _e_first_day(text: str) -> ScheduleIntent | None:
    """first day of every month / on the first"""
    if re.search(r"\bfirst\s+day\b", text):
        return ScheduleIntent(days_of_month=[1])
    dow_names = "|".join(WEEKDAYS.keys())
    if re.search(r"\bon\s+the\s+first\b(?!\s+(?:" + dow_names + r"))", text):
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
    weekday_only = bool(re.search(r"\b(?:weekdays?|workdays?)\b", text))
    return ScheduleIntent(
        excluded_days_of_month=[excluded],
        weekday_only=weekday_only,
    )


# ---------------------------------------------------------------------------
# Month enrichers (priorities 600-610)
# ---------------------------------------------------------------------------


@registry.register("quarter_months", priority=600, composite=False)
def _e_quarter_months(text: str) -> ScheduleIntent | None:
    """each quarter / every quarter / quarterly (not 'quarter hour/past/to/till/of')"""
    if re.search(r"\b(?:each|every)\s+quarter\b(?!\s+(?:hour|past|to|till|of))", text):
        return ScheduleIntent(months=QUARTER_MONTHS)
    return None


@registry.register("month_interval", priority=610, composite=False)
def _e_month_interval(text: str) -> ScheduleIntent | None:
    """every other month / every N months"""
    if re.search(r"\bevery\s+other\s+month\b", text):
        return ScheduleIntent(month_interval=2)
    m = re.search(r"\bevery\s+(\d+)\s+months?\b", text)
    if m:
        n = int(m.group(1))
        if not 1 <= n <= 12:
            raise ValueError(f"Month interval {n} is out of range (1-12)")
        return ScheduleIntent(month_interval=n)
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
