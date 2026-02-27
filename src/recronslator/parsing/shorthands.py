"""Cross-domain schedule-shape shorthands (daily, weekly, monthly, quarterly).

These composites span multiple domains (time + day + month) and serve as
top-level schedule recognisers.  They pre-fill sensible defaults (e.g.
midnight) that enrichers from other modules can override.
"""

from __future__ import annotations

import re

from recronslator.model import ScheduleIntent
from recronslator.parsing.constants import QUARTER_MONTHS, SPECIAL_TIMES, WEEKDAYS
from recronslator.parsing.registry import registry


# ---------------------------------------------------------------------------
# Helper predicates (private to this module)
# ---------------------------------------------------------------------------


def _text_has_explicit_time(text: str) -> bool:
    """Return True if the text contains an explicit time specification."""
    if re.search(r"\d{1,2}:\d{2}", text):
        return True
    if re.search(r"\d{1,2}\s*(?:am?|pm?)\b", text):
        return True
    return any(re.search(r"\b" + name + r"\b", text) for name in SPECIAL_TIMES)


def _text_has_explicit_dom(text: str) -> bool:
    """Return True if the text contains an explicit day-of-month reference."""
    if re.search(r"\b\d+(?:st|nd|rd|th)\b", text):
        return True
    if re.search(r"\b(?:first|last)\s+(?:\d+\s+)?days?\b", text):
        return True
    dow_names = "|".join(WEEKDAYS.keys())
    if re.search(r"\bon\s+the\s+first\b(?!\s+(?:" + dow_names + r"))", text):
        return True
    if re.search(r"\bday\s+\d+\b", text):
        return True
    return False


# ---------------------------------------------------------------------------
# Shorthand composites (priorities 202-207)
# ---------------------------------------------------------------------------


@registry.register("shorthand_weekly", priority=202)
def _p_shorthand_weekly(text: str) -> ScheduleIntent | None:
    """weekly on <day>"""
    m = re.search(r"\bweekly\b", text)
    if not m:
        return None
    for day_name, day_num in WEEKDAYS.items():
        if re.search(r"\b" + day_name + r"\b", text):
            return ScheduleIntent(minutes=[0], hours=[0], days_of_week=[day_num])
    return ScheduleIntent(minutes=[0], hours=[0])


@registry.register("shorthand_daily", priority=205)
def _p_shorthand_daily(text: str) -> ScheduleIntent | None:
    """daily / every day -- defaults to midnight; time enrichers override if time is present"""
    if "twice" in text:
        return None
    if not (re.search(r"\bdaily\b", text) or re.search(r"\bevery\s+day\b", text)):
        return None
    if _text_has_explicit_time(text):
        return ScheduleIntent()
    return ScheduleIntent(minutes=[0], hours=[0])


@registry.register("shorthand_monthly", priority=206)
def _p_shorthand_monthly(text: str) -> ScheduleIntent | None:
    """monthly / every month -- defaults to midnight on the 1st."""
    if not (re.search(r"\bmonthly\b", text) or re.search(r"\bevery\s+month\b", text)):
        return None
    has_dom = _text_has_explicit_dom(text)
    has_time = _text_has_explicit_time(text)
    if has_dom:
        return ScheduleIntent()
    if has_time:
        return ScheduleIntent(days_of_month=[1])
    return ScheduleIntent(minutes=[0], hours=[0], days_of_month=[1])


@registry.register("shorthand_quarterly", priority=207)
def _p_shorthand_quarterly(text: str) -> ScheduleIntent | None:
    """quarterly -- defaults to midnight on the 1st of each quarter month."""
    if not re.search(r"\bquarterly\b", text):
        return None
    has_dom = _text_has_explicit_dom(text)
    has_time = _text_has_explicit_time(text)
    if has_dom:
        return ScheduleIntent(months=QUARTER_MONTHS)
    if has_time:
        return ScheduleIntent(months=QUARTER_MONTHS, days_of_month=[1])
    return ScheduleIntent(
        minutes=[0], hours=[0], months=QUARTER_MONTHS, days_of_month=[1],
    )
