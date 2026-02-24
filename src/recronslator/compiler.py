"""Compiler: ScheduleIntent → CronExpression.

Pure function: no regex, no string parsing. This is where cron-specific
encoding lives (intervals as */N, ordinal weekdays as day-of-month ranges, etc.).
"""

from __future__ import annotations

import warnings

from recronslator.model import CronExpression, ScheduleIntent
from recronslator.validator import validate_expression


def compile_intent(intent: ScheduleIntent) -> CronExpression:
    """Convert a ScheduleIntent into a validated CronExpression.

    Raises ValueError if the intent cannot be expressed in standard 5-field cron.
    """
    minute = _compile_minute(intent)
    hour = _compile_hour(intent)
    day_of_month = _compile_day_of_month(intent)
    month = _compile_month(intent)
    day_of_week = _compile_day_of_week(intent)

    # Warn about day-of-month + day-of-week OR semantics
    if day_of_month != "*" and day_of_week != "*":
        # Ordinal weekday pattern is intentional — suppress warning for that case
        if intent.ordinal_weekday is None:
            warnings.warn(
                "This cron expression sets both day-of-month and day-of-week. "
                "Most cron daemons (including vixie cron) treat this as OR, "
                "not AND — the job will run when EITHER condition is true. "
                "See your cron documentation to confirm behavior.",
                UserWarning,
                stacklevel=4,
            )

    expr = CronExpression(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month=month,
        day_of_week=day_of_week,
    )
    validate_expression(expr)
    return expr


# ---------------------------------------------------------------------------
# Field compilers
# ---------------------------------------------------------------------------

def _compile_minute(intent: ScheduleIntent) -> str:
    if intent.minute_range is not None:
        lo, hi = intent.minute_range
        return f"{lo}-{hi}"

    if intent.minute_interval is not None:
        return f"*/{intent.minute_interval}"

    if intent.minutes is not None:
        return ",".join(str(m) for m in sorted(intent.minutes))

    # Default: if hours are set but no minutes specified, assume :00
    if intent.hours is not None:
        return "0"

    if intent.hour_interval is not None:
        return "0"

    # Default to :00 when day constraints exist but no time is specified
    if _has_day_constraint(intent):
        return "0"

    return "*"


def _has_day_constraint(intent: ScheduleIntent) -> bool:
    return any([
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


def _compile_hour(intent: ScheduleIntent) -> str:
    if intent.hour_interval is not None:
        return f"*/{intent.hour_interval}"

    if intent.hour_range is not None:
        start, end = intent.hour_range
        return f"{start}-{end}"

    if intent.hours is not None:
        return ",".join(str(h) for h in sorted(intent.hours))

    if intent.minute_interval is not None:
        return "*"

    if intent.minute_range is not None:
        return "*"

    # Default to midnight hour when day constraints exist but NO time is specified at all.
    # Exception: if minutes are explicitly set (e.g. "at :15 past each hour"), keep "*".
    if _has_day_constraint(intent) and intent.minutes is None:
        return "0"

    return "*"


def _compile_day_of_month(intent: ScheduleIntent) -> str:
    if intent.last_day_of_month:
        return "L"

    if intent.ordinal_weekday is not None:
        nth, _ = intent.ordinal_weekday
        # nth occurrence of a weekday falls within days (nth-1)*7+1 .. nth*7
        start = (nth - 1) * 7 + 1
        end = start + 6
        return f"{start}-{end}"

    if intent.excluded_days_of_month is not None:
        # Build explicit list of days excluding the exceptions
        excluded = set(intent.excluded_days_of_month)
        days = [d for d in range(1, 32) if d not in excluded]
        return _days_to_ranges(days)

    if intent.days_of_month is not None:
        if len(intent.days_of_month) == 1:
            return str(intent.days_of_month[0])
        # Multiple specific days
        return _days_to_ranges(intent.days_of_month)

    if intent.day_interval is not None:
        return f"*/{intent.day_interval}"

    return "*"


def _compile_month(intent: ScheduleIntent) -> str:
    if intent.months is not None:
        return ",".join(str(m) for m in sorted(intent.months))
    return "*"


def _compile_day_of_week(intent: ScheduleIntent) -> str:
    if intent.weekday_only:
        return "1-5"

    if intent.weekend_only:
        return "0,6"

    if intent.ordinal_weekday is not None:
        _, weekday = intent.ordinal_weekday
        return str(weekday)

    if intent.days_of_week is not None:
        return ",".join(str(d) for d in sorted(intent.days_of_week))

    return "*"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_to_ranges(days: list[int]) -> str:
    """Convert a sorted list of day integers to compact range notation.

    E.g. [1,2,3,4,5,6,7,8,9,10,11,12,14,15,...,31] → '1-12,14-31'
    """
    if not days:
        return "*"
    days = sorted(days)
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
