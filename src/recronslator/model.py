"""Core domain model for recronslator.

Two dataclasses represent the two sides of a schedule:
- ScheduleIntent: a structured, human-meaningful representation
- CronExpression: the cron-syntax representation with validation
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScheduleIntent:
    """A structured representation of a schedule, independent of cron syntax.

    Separates *what the user means* from *how cron expresses it*, allowing
    both translation directions to share a common intermediate form.
    """

    # Time of day — specific values
    minutes: list[int] | None = None
    hours: list[int] | None = None

    # Time of day — interval-based
    minute_interval: int | None = None
    hour_interval: int | None = None

    # Constrained hour window (e.g. "between 9am and 5pm")
    hour_range: tuple[int, int] | None = None

    # Minute range (e.g. "first 15 minutes of each hour" → "0-14")
    minute_range: tuple[int, int] | None = None

    # Day of month — specific values
    days_of_month: list[int] | None = None
    day_interval: int | None = None
    last_day_of_month: bool = False

    # Ordinal weekday: (nth, weekday_int) e.g. (1, 1) for "first Monday"
    ordinal_weekday: tuple[int, int] | None = None

    # Day of week
    days_of_week: list[int] | None = None
    weekday_only: bool = False    # shorthand for Mon-Fri
    weekend_only: bool = False    # shorthand for Sat-Sun

    # Month
    months: list[int] | None = None

    # Exception days to exclude from day_of_month
    excluded_days_of_month: list[int] | None = None



@dataclass
class CronExpression:
    """A validated 5-field cron expression.

    Optional second/year fields are reserved for future extended-format support
    and are never emitted in standard mode.
    """

    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"

    # Reserved for future 6/7-field support — not used in v1.0
    second: str | None = None
    year: str | None = None

    def validate(self) -> None:
        """Raise ValueError if any field is out of valid cron range."""
        _validate_minute_field(self.minute)
        _validate_hour_field(self.hour)
        _validate_dom_field(self.day_of_month)
        _validate_month_field(self.month)
        _validate_dow_field(self.day_of_week)

    def __str__(self) -> str:
        return (
            f"{self.minute} {self.hour} {self.day_of_month} "
            f"{self.month} {self.day_of_week}"
        )


# ---------------------------------------------------------------------------
# Internal field validators (used by CronExpression.validate and validator.py)
# ---------------------------------------------------------------------------

def _validate_minute_field(value: str) -> None:
    if value == "*":
        return
    # Handle step: */N or M-N/S
    if "/" in value:
        base, step = value.rsplit("/", 1)
        if not step.isdigit():
            raise ValueError(f"Invalid minute field: {value!r}")
        n = int(step)
        if not 1 <= n <= 59:
            raise ValueError(f"Minute step {n} is out of range (1-59)")
        if base == "*":
            return
        value = base
    # Handle comma-separated values and ranges
    for part in value.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            for x in (lo, hi):
                if not x.isdigit():
                    raise ValueError(f"Invalid minute field: {value!r}")
                n = int(x)
                if not 0 <= n <= 59:
                    raise ValueError(f"Minute value {n} is out of range (0-59)")
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid minute field: {value!r}")
            n = int(part)
            if not 0 <= n <= 59:
                raise ValueError(f"Minute value {n} is out of range (0-59)")


def _validate_hour_field(value: str) -> None:
    if value == "*":
        return
    if "/" in value:
        base, step = value.rsplit("/", 1)
        if not step.isdigit():
            raise ValueError(f"Invalid hour field: {value!r}")
        n = int(step)
        if not 1 <= n <= 23:
            raise ValueError(f"Hour step {n} is out of range (1-23)")
        if base == "*":
            return
        value = base
    for part in value.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            for x in (lo, hi):
                if not x.isdigit():
                    raise ValueError(f"Invalid hour field: {value!r}")
                n = int(x)
                if not 0 <= n <= 23:
                    raise ValueError(f"Hour value {n} is out of range (0-23)")
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid hour field: {value!r}")
            n = int(part)
            if not 0 <= n <= 23:
                raise ValueError(f"Hour value {n} is out of range (0-23)")


def _validate_dom_field(value: str) -> None:
    if value in ("*", "L"):
        return
    if "/" in value:
        base, step = value.rsplit("/", 1)
        if not step.isdigit():
            raise ValueError(f"Invalid day-of-month field: {value!r}")
        n = int(step)
        if not 1 <= n <= 31:
            raise ValueError(f"Day-of-month step {n} is out of range (1-31)")
        if base == "*":
            return
        value = base
    for part in value.split(","):
        if part == "L":
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            for x in (lo, hi):
                if not x.isdigit():
                    raise ValueError(f"Invalid day-of-month field: {value!r}")
                n = int(x)
                if not 1 <= n <= 31:
                    raise ValueError(f"Day-of-month value {n} is out of range (1-31)")
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid day-of-month field: {value!r}")
            n = int(part)
            if not 1 <= n <= 31:
                raise ValueError(f"Day-of-month value {n} is out of range (1-31)")


def _validate_month_field(value: str) -> None:
    if value == "*":
        return
    if "/" in value:
        base, step = value.rsplit("/", 1)
        if not step.isdigit():
            raise ValueError(f"Invalid month field: {value!r}")
        n = int(step)
        if not 1 <= n <= 12:
            raise ValueError(f"Month step {n} is out of range (1-12)")
        if base == "*":
            return
        value = base
    for part in value.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            for x in (lo, hi):
                if not x.isdigit():
                    raise ValueError(f"Invalid month field: {value!r}")
                n = int(x)
                if not 1 <= n <= 12:
                    raise ValueError(f"Month value {n} is out of range (1-12)")
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid month field: {value!r}")
            n = int(part)
            if not 1 <= n <= 12:
                raise ValueError(f"Month value {n} is out of range (1-12)")


def _validate_dow_field(value: str) -> None:
    if value == "*":
        return
    for part in value.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            for x in (lo, hi):
                if not x.isdigit():
                    raise ValueError(f"Invalid day-of-week field: {value!r}")
                n = int(x)
                if not 0 <= n <= 6:
                    raise ValueError(f"Day-of-week value {n} is out of range (0-6)")
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid day-of-week field: {value!r}")
            n = int(part)
            if not 0 <= n <= 6:
                raise ValueError(f"Day-of-week value {n} is out of range (0-6)")
