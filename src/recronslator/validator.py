"""Validation logic for ScheduleIntent and CronExpression.

All range-checking and constraint logic lives here in one place, separate
from parsing and compilation, so it can be unit-tested independently and
reused by both directions of translation.
"""

from __future__ import annotations

from recronslator.model import (
    CronExpression,
    ScheduleIntent,
    _validate_minute_field,
    _validate_hour_field,
    _validate_dom_field,
    _validate_month_field,
    _validate_dow_field,
)


def validate_intent(intent: ScheduleIntent) -> None:
    """Raise ValueError if the intent contains invalid or contradictory values.

    Checks:
    - Minute/hour/day/month/weekday values are within valid cron ranges
    - Intervals are expressible as */N
    - Inexpressible schedules are rejected with a clear message
    """
    if intent.minutes is not None:
        for m in intent.minutes:
            if not 0 <= m <= 59:
                raise ValueError(f"Minute value {m} is out of range (0-59)")

    if intent.hours is not None:
        for h in intent.hours:
            if not 0 <= h <= 23:
                raise ValueError(f"Hour value {h} is out of range (0-23)")

    if intent.minute_interval is not None:
        if not 1 <= intent.minute_interval <= 59:
            raise ValueError(
                f"Minute interval {intent.minute_interval} is out of range (1-59)"
            )

    if intent.hour_interval is not None:
        if not 1 <= intent.hour_interval <= 23:
            raise ValueError(
                f"Hour interval {intent.hour_interval} is out of range (1-23)"
            )

    if intent.hour_range is not None:
        start, end = intent.hour_range
        if not 0 <= start <= 23:
            raise ValueError(f"Hour range start {start} is out of range (0-23)")
        if not 0 <= end <= 23:
            raise ValueError(f"Hour range end {end} is out of range (0-23)")

    if intent.minute_range is not None:
        lo, hi = intent.minute_range
        if not 0 <= lo <= 59 or not 0 <= hi <= 59:
            raise ValueError(
                f"Minute range {lo}-{hi} contains values out of range (0-59)"
            )

    if intent.days_of_month is not None:
        for d in intent.days_of_month:
            if not 1 <= d <= 31:
                raise ValueError(f"Day-of-month value {d} is out of range (1-31)")

    if intent.excluded_days_of_month is not None:
        for d in intent.excluded_days_of_month:
            if not 1 <= d <= 31:
                raise ValueError(
                    f"Excluded day-of-month value {d} is out of range (1-31)"
                )

    if intent.day_interval is not None:
        if not 1 <= intent.day_interval <= 31:
            raise ValueError(
                f"Day interval {intent.day_interval} is out of range (1-31)"
            )

    if intent.days_of_week is not None:
        for d in intent.days_of_week:
            if not 0 <= d <= 6:
                raise ValueError(f"Day-of-week value {d} is out of range (0-6)")

    if intent.excluded_days_of_week is not None:
        for d in intent.excluded_days_of_week:
            if not 0 <= d <= 6:
                raise ValueError(
                    f"Excluded day-of-week value {d} is out of range (0-6)"
                )

    if intent.months is not None:
        for m in intent.months:
            if not 1 <= m <= 12:
                raise ValueError(f"Month value {m} is out of range (1-12)")

    if intent.month_interval is not None:
        if not 1 <= intent.month_interval <= 12:
            raise ValueError(
                f"Month interval {intent.month_interval} is out of range (1-12)"
            )

    if intent.last_weekday_of_month is not None:
        if not 0 <= intent.last_weekday_of_month <= 6:
            raise ValueError(
                f"last_weekday_of_month {intent.last_weekday_of_month} is out of range (0-6)"
            )

    if intent.ordinal_weekday is not None:
        nth, weekday = intent.ordinal_weekday
        if not 1 <= nth <= 5:
            raise ValueError(
                f"Ordinal {nth} is out of range (1-5); cron supports at most the 5th occurrence"
            )
        if not 0 <= weekday <= 6:
            raise ValueError(f"Weekday {weekday} is out of range (0-6)")

    # Mutual-exclusion guards
    if intent.weekday_only and intent.weekend_only:
        raise ValueError("weekday_only and weekend_only cannot both be True")

    _check_is_not_empty(intent)


def _check_is_not_empty(intent: ScheduleIntent) -> None:
    """Raise ValueError if the intent has no meaningful content."""
    has_time = any([
        intent.minutes is not None,
        intent.hours is not None,
        intent.minute_interval is not None,
        intent.hour_interval is not None,
        intent.hour_range is not None,
        intent.minute_range is not None,
    ])
    has_day = any([
        intent.days_of_month is not None,
        intent.day_interval is not None,
        intent.last_day_of_month,
        intent.ordinal_weekday is not None,
        intent.last_weekday_of_month is not None,
        intent.days_of_week is not None,
        intent.weekday_only,
        intent.weekend_only,
        intent.months is not None,
        intent.month_interval is not None,
        intent.excluded_days_of_month is not None,
        intent.excluded_days_of_week is not None,
    ])
    if not has_time and not has_day:
        raise ValueError("Could not understand the schedule description")


def validate_expression(expr: CronExpression) -> None:
    """Raise ValueError if any cron field is out of range."""
    try:
        _validate_minute_field(expr.minute)
        _validate_hour_field(expr.hour)
        _validate_dom_field(expr.day_of_month)
        _validate_month_field(expr.month)
        _validate_dow_field(expr.day_of_week)
    except ValueError:
        raise
