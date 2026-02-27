"""Describer: CronExpression → English string.

Parses cron fields and generates the most natural phrasing following the
detection priority from the engineering plan (Section 5).
"""

from __future__ import annotations

import re

from recronslator.model import CronExpression
from recronslator.validator import validate_expression


_WEEKDAY_NAMES = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
]
_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_ORDINAL_NAMES = ["", "first", "second", "third", "fourth", "fifth"]


def describe(expression: str) -> str:
    """Convert a 5-field cron expression string to a human-readable description.

    Example: "0 3 * * 1" → "Every Monday at 3:00 AM"

    Raises ValueError for invalid cron expressions.
    """
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(
            f"Expected 5-field cron expression, got {len(fields)} fields: {expression!r}"
        )
    minute_f, hour_f, dom_f, month_f, dow_f = fields

    expr = CronExpression(
        minute=minute_f,
        hour=hour_f,
        day_of_month=dom_f,
        month=month_f,
        day_of_week=dow_f,
    )
    validate_expression(expr)

    return _build_description(minute_f, hour_f, dom_f, month_f, dow_f)


def _build_description(
    minute: str, hour: str, dom: str, month: str, dow: str
) -> str:
    parts = [
        _describe_time(minute, hour),
        _describe_day(dom, dow),
        _describe_month(month),
    ]
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Time description
# ---------------------------------------------------------------------------

def _describe_time(minute: str, hour: str) -> str:
    # Priority 0: wildcard minute with constrained hour → "Every minute between X and Y"
    # e.g. "* 9-17 * * *" → "Every minute between 9:00 AM and 5:00 PM"
    # Exclude step patterns (*/N) — those are hour intervals handled by Priority 2.
    if minute == "*" and hour != "*" and not re.fullmatch(r"\*/\d+", hour):
        return f"Every minute {_describe_hour_constraint(hour)}"

    # Priority 1: interval in minute field
    m = re.fullmatch(r"\*/(\d+)", minute)
    if m:
        interval = int(m.group(1))
        base = f"Every {interval} minute{'s' if interval != 1 else ''}"
        if hour != "*":
            hr_desc = _describe_hour_constraint(hour)
            return f"{base} {hr_desc}"
        return base

    # Priority 2: interval in hour field
    m = re.fullmatch(r"\*/(\d+)", hour)
    if m:
        interval = int(m.group(1))
        base = f"Every {interval} hour{'s' if interval != 1 else ''}"
        # Include the minute offset when it is non-zero (e.g. "30 */2 * * *")
        mn_m = re.fullmatch(r"(\d+)", minute)
        if mn_m and int(mn_m.group(1)) != 0:
            return f"{base} at {_fmt_minute(int(mn_m.group(1)))}"
        return base

    # Priority 2.5: specific minute with contiguous hour range → "every hour between X and Y"
    # e.g. "0 9-17 * * *" → "Every hour between 9:00 AM and 5:00 PM"
    # e.g. "30 9-17 * * *" → "Every hour at :30 between 9:00 AM and 5:00 PM"
    m_hr = re.fullmatch(r"(\d+)-(\d+)", hour)
    m_mn = re.fullmatch(r"(\d+)", minute)
    if m_hr and m_mn:
        start = _fmt_hour(int(m_hr.group(1)))
        end = _fmt_hour(int(m_hr.group(2)))
        mn = int(m_mn.group(1))
        if mn == 0:
            return f"Every hour between {start} and {end}"
        return f"Every hour at {_fmt_minute(mn)} between {start} and {end}"

    # Priority 3: minute range (e.g. "0-14")
    m = re.fullmatch(r"(\d+)-(\d+)", minute)
    if m and hour == "*":
        lo, hi = int(m.group(1)), int(m.group(2))
        return f"Once per hour in the first {hi + 1} minutes"

    # Priority 4: list patterns / specific values
    hours_list = _parse_field_list(hour)
    minutes_list = _parse_field_list(minute)

    if hours_list is None and minutes_list is None:
        # both wildcards
        return "Every minute"

    if hours_list is None:
        # minute is specific but hour is wildcard
        if not minutes_list:
            return "At :00 past every hour"
        if len(minutes_list) == 1:
            return f"At {_fmt_minute(minutes_list[0])} past every hour"
        # Multiple minute offsets (e.g. "15,30,45 * * * *")
        formatted = [_fmt_minute(mn) for mn in minutes_list]
        return f"At {_oxford_join(formatted)} past every hour"

    return _fmt_time_list(hours_list, minutes_list)


def _describe_hour_constraint(hour: str) -> str:
    # Step pattern: */N → "every N hours"
    m = re.fullmatch(r"\*/(\d+)", hour)
    if m:
        n = int(m.group(1))
        return f"every {n} hour{'s' if n != 1 else ''}"
    m = re.fullmatch(r"(\d+)-(\d+)", hour)
    if m:
        start = _fmt_hour(int(m.group(1)))
        end = _fmt_hour(int(m.group(2)))
        return f"between {start} and {end}"
    # Single numeric hour (e.g. "15" → "at 3:00 PM")
    try:
        return f"at {_fmt_hour(int(hour))}"
    except ValueError:
        pass
    # Comma-separated hour list (e.g. "9,17" → "at 9:00 AM and 5:00 PM")
    hours = _parse_field_list(hour)
    if hours:
        formatted = [_fmt_hour(h) for h in hours]
        if len(formatted) == 1:
            return f"at {formatted[0]}"
        return f"at {_oxford_join(formatted)}"
    return f"in hour {hour}"


def _fmt_time_list(hours: list[int], minutes: list[int] | None) -> str:
    mn = minutes[0] if minutes and len(set(minutes)) == 1 else 0
    if minutes and len(set(minutes)) > 1:
        # e.g. "15,30,45 * * * *" — unusual; just list minutes
        mn_list = ", ".join(_fmt_clock(h, m) for h in hours for m in minutes)
        return f"At {mn_list}"

    if len(hours) == 1:
        h = hours[0]
        return _describe_single_time(h, mn)

    # Multiple hours
    return f"At {_oxford_join([_fmt_clock(h, mn) for h in sorted(hours)])}"


def _describe_single_time(hour: int, minute: int) -> str:
    if hour == 0 and minute == 0:
        return "At midnight"
    if hour == 12 and minute == 0:
        return "At noon"
    return f"At {_fmt_clock(hour, minute)}"


def _fmt_clock(hour: int, minute: int) -> str:
    """Format as '3:00 AM' / '4:30 PM'."""
    meridiem = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {meridiem}"


def _fmt_hour(hour: int) -> str:
    """Format just an hour as '9:00 AM' etc."""
    return _fmt_clock(hour, 0)


def _fmt_minute(minute: int) -> str:
    return f":{minute:02d}"


def _oxford_join(items: list[str]) -> str:
    """Join 2+ items into natural English with an Oxford comma.

    _oxford_join(["a", "b"])        → "a and b"
    _oxford_join(["a", "b", "c"])   → "a, b, and c"
    """
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _parse_field_list(field: str) -> list[int] | None:
    """Return a sorted list of concrete integer values, or None for wildcard."""
    if field == "*":
        return None
    values: list[int] = []
    for part in field.split(","):
        if "-" in part and "/" not in part:
            lo, hi = part.split("-")
            values.extend(range(int(lo), int(hi) + 1))
        elif "/" in part:
            return None  # Step pattern; caller handles separately
        elif re.fullmatch(r"\d+L", part):
            return None  # NL notation; caller handles separately
        else:
            values.append(int(part))
    return sorted(set(values))


# ---------------------------------------------------------------------------
# Day description
# ---------------------------------------------------------------------------

def _describe_day(dom: str, dow: str) -> str:
    dow_desc = _describe_dow(dow)
    dom_desc = _describe_dom(dom, dow)

    if dow_desc and dom_desc:
        # Ordinal weekday pattern: dom_desc already embeds the day name
        # (e.g. "on the first Monday of every month"), so dow_desc ("every Monday")
        # would be redundant.  Only suppress when _describe_dom actually took the
        # ordinal path — which requires both a 7-day DOM range AND a single DOW value.
        m = re.fullmatch(r"(\d+)-(\d+)", dom)
        dow_val = _parse_field_list(dow)
        if m and int(m.group(2)) - int(m.group(1)) == 6 and dow_val and len(dow_val) == 1:
            return dom_desc
        return f"{dom_desc} {dow_desc}"
    return dow_desc or dom_desc or ""


def _describe_dow(dow: str) -> str:
    if dow == "*":
        return ""
    if dow == "1-5":
        return "on weekdays"
    if dow in ("0,6", "6,0"):
        return "on weekends"
    # NL notation: e.g. "5L" means "last Friday of the month"
    m = re.fullmatch(r"(\d)L", dow)
    if m:
        day_name = _WEEKDAY_NAMES[int(m.group(1))]
        return f"on the last {day_name} of every month"
    days = _parse_field_list(dow)
    if days is None:
        return f"on day-of-week {dow}"
    if len(days) == 1:
        return f"every {_WEEKDAY_NAMES[days[0]]}"
    names = [_WEEKDAY_NAMES[d] for d in days]
    return f"every {_oxford_join(names)}"


def _describe_dom(dom: str, dow: str) -> str:
    if dom == "*":
        return ""
    if dom == "L":
        return "on the last day of every month"

    # Ordinal weekday pattern: dom is a range like "1-7", "8-14" + dow is a weekday
    if dow != "*" and re.fullmatch(r"\d+-\d+", dom):
        lo, hi = map(int, dom.split("-"))
        # Which ordinal? (lo-1)//7 + 1
        nth = (lo - 1) // 7 + 1
        if 1 <= nth <= 5 and hi - lo == 6:
            dow_val = _parse_field_list(dow)
            if dow_val and len(dow_val) == 1:
                day_name = _WEEKDAY_NAMES[dow_val[0]]
                return f"on the {_ORDINAL_NAMES[nth]} {day_name} of every month"

    # Explicit short day list (e.g. "1,15" → "on the 1st and 15th of every month")
    # Detect before the general range/exception logic to produce clean output.
    if "," in dom and "-" not in dom:
        days = _parse_field_list(dom)
        if days:
            formatted = [_ordinal(d) for d in days]
            if len(formatted) == 1:
                return f"on the {formatted[0]} of every month"
            return f"on the {_oxford_join(formatted)} of every month"

    # Exception / range pattern (e.g. "1-12,14-31")
    if "," in dom or re.search(r"\d+-\d+", dom):
        # Try to find excluded day
        all_days: set[int] = set(range(1, 32))
        included: set[int] = set()
        for part in dom.split(","):
            m = re.fullmatch(r"(\d+)-(\d+)", part)
            if m:
                included.update(range(int(m.group(1)), int(m.group(2)) + 1))
            else:
                included.add(int(part))
        excluded = all_days - included
        if len(excluded) == 1:
            ex = list(excluded)[0]
            return f"except the {_ordinal(ex)} of the month"
        return f"on days {dom} of the month"

    # Single specific day
    try:
        day = int(dom)
        return f"on the {_ordinal(day)} of every month"
    except ValueError:
        pass

    # Step
    m = re.fullmatch(r"\*/(\d+)", dom)
    if m:
        n = int(m.group(1))
        return f"every {n} day{'s' if n != 1 else ''}"

    return f"on day {dom}"


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# Month description
# ---------------------------------------------------------------------------

def _describe_month(month: str) -> str:
    if month == "*":
        return ""
    if month == "1,4,7,10":
        return "each quarter"
    # Step notation: */N
    m = re.fullmatch(r"\*/(\d+)", month)
    if m:
        n = int(m.group(1))
        if n == 2:
            return "every other month"
        return f"every {n} month{'s' if n != 1 else ''}"
    months = _parse_field_list(month)
    if months is None:
        return f"in month {month}"
    names = [_MONTH_NAMES[m] for m in months]
    if len(names) == 1:
        return f"in {names[0]}"
    return f"in {_oxford_join(names)}"
