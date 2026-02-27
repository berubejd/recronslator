"""Time-related composite patterns and enrichers.

Composites (priorities 97-214) recognise the core time shape of a schedule:
  - minute/hour intervals ("every 5 minutes", "every 2 hours")
  - hourly shorthands ("on the hour", "quarter past", "half hour")
  - colon-past-hour ("at :30 past every hour")

Enrichers (priorities 298-335) layer specific times onto any composite:
  - colon-format time lists ("at 9:15 AM, 9:30 AM, 9:45 AM")
  - bare am/pm times ("at 3pm")
  - minute offsets ("at :30")
  - minute ranges ("in the first 15 minutes")
  - hour ranges ("between 9am and 5pm")
"""

from __future__ import annotations

import re

from recronslator.model import ScheduleIntent
from recronslator.parsing.constants import BUSINESS_HOURS, SPECIAL_TIMES
from recronslator.parsing.helpers import (
    parse_multiple_times,
    parse_time_range,
    parse_time_token,
)
from recronslator.parsing.registry import registry

# Shared regex fragments
_LIST_SEP = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+)"
_SPECIAL_NAME_ALT = "|".join(re.escape(k) for k in SPECIAL_TIMES)

# ---------------------------------------------------------------------------
# Interval composites (priorities 97-120)
# ---------------------------------------------------------------------------


@registry.register("every_minute_hour_interval", priority=97)
def _p_every_minute_hour_interval(text: str) -> ScheduleIntent | None:
    """every minute every N hours"""
    m = re.search(r"every\s+minute\s+every\s+(\d+)\s+hours?", text)
    if not m:
        return None
    return ScheduleIntent(minute_interval=1, hour_interval=int(m.group(1)))


@registry.register("every_minute_ranged", priority=98)
def _p_every_minute_ranged(text: str) -> ScheduleIntent | None:
    """every minute between Xam and Ypm / from Xam to Ypm [on weekdays]"""
    if not re.search(r"\bevery\s+minute\b", text):
        return None
    if "between" not in text and not re.search(r"\bfrom\s+\d", text):
        return None
    hr = parse_time_range(text)
    if hr is None:
        return None
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(minute_interval=1, hour_range=hr, weekday_only=weekday_only)


@registry.register("every_minute", priority=99)
def _p_every_minute(text: str) -> ScheduleIntent | None:
    """every minute (no explicit number, no time range)"""
    if not re.search(r"\bevery\s+minute\b", text):
        return None
    if "between" in text or re.search(r"\bfrom\s+\d", text):
        return None
    if "business hours" in text:
        return None
    if re.search(r"every\s+\d+\s+hours?", text):
        return None
    return ScheduleIntent(minute_interval=1)


@registry.register("minute_interval_ranged", priority=100)
def _p_minute_interval_ranged(text: str) -> ScheduleIntent | None:
    """every N minutes between Xam and Ypm / from Xam to Ypm [on weekdays]"""
    m = re.search(r"every\s+(\d+)\s+minutes?.*(?:between|from\s+\d)", text)
    if not m:
        return None
    interval = int(m.group(1))
    if interval > 59:
        raise ValueError(f"Minute interval {interval} is out of range (1-59)")
    hr = parse_time_range(text)
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
    if re.search(r"\bfrom\s+\d{1,2}.*\bto\b", text):
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
    """every N hours (not 'every hour' -- that's shorthand_hourly)"""
    m = re.search(r"every\s+(\d+)\s+hours?", text)
    if not m:
        return None
    interval = int(m.group(1))
    if interval == 1:
        return ScheduleIntent(minutes=[0])
    if interval > 23:
        raise ValueError(f"Hour interval {interval} is out of range (1-23)")
    return ScheduleIntent(hour_interval=interval)


@registry.register("hour_interval_enricher", priority=115, composite=False)
def _e_hour_interval(text: str) -> ScheduleIntent | None:
    """every N hours -- enricher to layer onto minute-interval composites"""
    m = re.search(r"every\s+(\d+)\s+hours?", text)
    if not m:
        return None
    interval = int(m.group(1))
    if interval <= 1 or interval > 23:
        return None
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
# Special time composites (priorities 190-214)
# ---------------------------------------------------------------------------


@registry.register("hourly_ranged", priority=190)
def _p_hourly_ranged(text: str) -> ScheduleIntent | None:
    """every hour / hourly between Xam and Ypm / from Xam to Ypm [on weekdays]"""
    if not (re.search(r"\bhourly\b", text) or re.search(r"\bevery\s+hour\b", text)):
        return None
    if "between" not in text and not re.search(r"\bfrom\s+\d", text):
        return None
    hr = parse_time_range(text)
    if hr is None:
        return None
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    mn_m = re.search(r"\bat\s+:(\d{2})\b", text)
    mn = int(mn_m.group(1)) if mn_m else 0
    return ScheduleIntent(minutes=[mn], hour_range=hr, weekday_only=weekday_only)


@registry.register("colon_past_every_hour", priority=199)
def _p_colon_past_every_hour(text: str) -> ScheduleIntent | None:
    """at :NN[, :NN, and :NN] past every hour [on weekdays]"""
    if "past" not in text:
        return None
    before_past = text.split("past")[0]
    tokens = re.findall(r":(\d{2})", before_past)
    if not tokens:
        return None
    minutes = sorted(int(t) for t in tokens)
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(minutes=minutes, weekday_only=weekday_only)


@registry.register("shorthand_hourly", priority=200)
def _p_shorthand_hourly(text: str) -> ScheduleIntent | None:
    """hourly / every hour (no time range -- ranged form handled by hourly_ranged)"""
    if not (re.search(r"\bhourly\b", text) or re.search(r"\bevery\s+hour\b", text)):
        return None
    if re.search(r":\d{2}\s+past\b", text):
        return None
    if "half hour" in text or "half past" in text:
        return None
    if "quarter past" in text or "quarter after" in text:
        return None
    if re.search(r"\bquarter\s+(?:to|till|of)\b", text):
        return None
    if "between" in text or re.search(r"\bfrom\s+\d", text):
        return None
    return ScheduleIntent(minutes=[0])


@registry.register("twice_daily", priority=203)
def _p_twice_daily(text: str) -> ScheduleIntent | None:
    """twice daily at H:MM and H:MM"""
    if "twice daily" not in text and "twice a day" not in text:
        return None
    m = re.search(
        r"at\s+([\d:]+\s*(?:am?|pm?)?)\s+and\s+([\d:]+\s*(?:am?|pm?)?)",
        text,
    )
    if not m:
        return None
    t1 = parse_time_token(m.group(1).strip())
    t2 = parse_time_token(m.group(2).strip())
    hours = sorted({t1[0], t2[0]})
    minutes_set = {t1[1], t2[1]}
    mn = list(minutes_set)[0] if len(minutes_set) == 1 else 0
    return ScheduleIntent(minutes=[mn], hours=hours)


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
    hr = parse_time_range(text)
    return ScheduleIntent(minute_interval=15, hour_range=hr)


@registry.register("quarter_past", priority=212)
def _p_quarter_past(text: str) -> ScheduleIntent | None:
    """(weekdays) at quarter past / quarter after each hour"""
    if "quarter past" not in text and "quarter after" not in text:
        return None
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(minutes=[15], weekday_only=weekday_only)


@registry.register("quarter_to", priority=213)
def _p_quarter_to(text: str) -> ScheduleIntent | None:
    """(weekdays) at quarter to / till / of each hour"""
    if not re.search(r"\bquarter\s+(?:to|till|of)\b", text):
        return None
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(minutes=[45], weekday_only=weekday_only)


@registry.register("on_the_hour", priority=214)
def _p_on_the_hour(text: str) -> ScheduleIntent | None:
    """on the hour / top of the hour [between X and Y] [on weekdays]"""
    if "on the hour" not in text and "top of the hour" not in text:
        return None
    hr = parse_time_range(text)
    weekday_only = bool(re.search(r"\bweekdays?\b", text))
    return ScheduleIntent(minutes=[0], hour_range=hr, weekday_only=weekday_only)


# ---------------------------------------------------------------------------
# Time enrichers (priorities 298-335)
# ---------------------------------------------------------------------------


@registry.register("mixed_times_list", priority=298, composite=False)
def _e_mixed_times_list(text: str) -> ScheduleIntent | None:
    """at 8am, noon, and 6pm -- multiple times where one or more are special names."""
    if "per hour" in text:
        return None
    digit_token = r"\d{1,2}(?::\d{2})?\s*(?:am?|pm?)?"
    token = rf"(?:{digit_token}|{_SPECIAL_NAME_ALT})"
    m = re.search(rf"\bat\s+({token}(?:{_LIST_SEP}{token})+)", text)
    if not m:
        return None
    raw_list = m.group(1)
    if not any(re.search(r"\b" + k + r"\b", raw_list) for k in SPECIAL_TIMES):
        return None
    parts = re.split(_LIST_SEP, raw_list)
    times = [parse_time_token(p.strip()) for p in parts if p.strip()]
    if len(times) < 2:
        return None
    hours = sorted({h for h, _ in times})
    minutes_set = {mn for _, mn in times}
    mn = list(minutes_set)[0] if len(minutes_set) == 1 else 0
    return ScheduleIntent(minutes=[mn], hours=hours)


@registry.register("colon_times_list", priority=299, composite=False)
def _e_colon_times_list(text: str) -> ScheduleIntent | None:
    """at H:MM am, H:MM pm[, and H:MM pm] -- two or more colon-format times"""
    _token = r"\d{1,2}:\d{2}\s*(?:am?|pm?)?"
    m = re.search(rf"\bat\s+({_token}(?:{_LIST_SEP}{_token})+)", text)
    if not m:
        return None
    raw_list = m.group(1)
    parts = re.split(_LIST_SEP, raw_list)
    times = [parse_time_token(p.strip()) for p in parts if p.strip()]
    if len(times) < 2:
        return None
    unique_hours = sorted({h for h, _ in times})
    unique_minutes = sorted({mn for _, mn in times})
    if len(unique_hours) == 1 and len(unique_minutes) > 1:
        return ScheduleIntent(minutes=unique_minutes, hours=unique_hours)
    mn = unique_minutes[0] if len(unique_minutes) == 1 else 0
    return ScheduleIntent(minutes=[mn], hours=unique_hours)


@registry.register("times_per_hour", priority=299, composite=False)
def _e_times_per_hour_early(text: str) -> ScheduleIntent | None:
    """N times per hour at M1, M2, and M3 minutes"""
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
    if "per hour" in text:
        return None
    m = re.search(
        rf"\bat\s+((?:\d{{1,2}}\s*(?:am?|pm?)?{_LIST_SEP})+\d{{1,2}}\s*(?:am?|pm?)?)",
        text,
    )
    if not m:
        return None

    raw_list = m.group(1)
    if ":" in raw_list:
        return None

    times = parse_multiple_times(raw_list)
    if len(times) < 2:
        return None
    hours = sorted({h for h, _ in times})
    minutes = sorted({mn for _, mn in times})
    mn = minutes[0] if len(set(minutes)) == 1 else 0
    return ScheduleIntent(minutes=[mn], hours=hours)


@registry.register("specific_time_with_minutes", priority=301, composite=False)
def _e_specific_time_with_minutes(text: str) -> ScheduleIntent | None:
    """at H:MM [am/pm] -- only for times with explicit minutes (colon format)"""
    m = re.search(
        r"\bat\s+(\d{1,2}:\d{2}\s*(?:am?|pm?)?)",
        text,
    )
    if not m:
        m = re.search(r"(\d{1,2}:\d{2}\s*(?:am?|pm?)?)", text)
        if not m:
            return None
    h, mn = parse_time_token(m.group(1).strip())
    return ScheduleIntent(minutes=[mn], hours=[h])


@registry.register("special_time_name", priority=302, composite=False)
def _e_special_time_name(text: str) -> ScheduleIntent | None:
    """at midnight / at noon / at dawn"""
    for name, (h, mn) in SPECIAL_TIMES.items():
        if re.search(r"\b" + name + r"\b", text):
            return ScheduleIntent(minutes=[mn], hours=[h])
    return None


@registry.register("single_bare_time", priority=303, composite=False)
def _e_single_bare_time(text: str) -> ScheduleIntent | None:
    """at Xam / at Xpm -- bare hour with am/pm marker, no colon"""
    m = re.search(r"\bat\s+(\d{1,2})\s*(am?|pm?)\b", text)
    if not m:
        return None
    token = m.group(1) + m.group(2)
    h, mn = parse_time_token(token)
    return ScheduleIntent(minutes=[mn], hours=[h])


@registry.register("colon_minute_offset", priority=305, composite=False)
def _e_colon_minute_offset(text: str) -> ScheduleIntent | None:
    """at :NN -- bare colon-minute offset (e.g. 'every 2 hours at :30')"""
    m = re.search(r"\bat\s+:(\d{2})\b", text)
    if not m:
        return None
    return ScheduleIntent(minutes=[int(m.group(1))])


@registry.register("first_n_minutes", priority=330, composite=False)
def _e_first_n_minutes(text: str) -> ScheduleIntent | None:
    """once per hour in the first N minutes"""
    m = re.search(r"(?:once per hour\s+)?in the first\s+(\d+)\s+minutes?", text)
    if not m:
        return None
    n = int(m.group(1)) - 1  # "first 15 minutes" -> 0-14
    return ScheduleIntent(minute_range=(0, n))


@registry.register("minute_range_span", priority=331, composite=False)
def _e_minute_range_span(text: str) -> ScheduleIntent | None:
    """in minutes :MM through :NN / in minute MM to NN"""
    m = re.search(
        r"\bin\s+minutes?\s+:?(\d{1,2})\s*(?:through|to|-)\s+:?(\d{1,2})\b",
        text,
    )
    if not m:
        return None
    lo, hi = int(m.group(1)), int(m.group(2))
    return ScheduleIntent(minute_range=(lo, hi))


@registry.register("time_range_enricher", priority=335, composite=False)
def _e_time_range(text: str) -> ScheduleIntent | None:
    """between Xam and Ypm / from Xam to Ypm -- enricher for hour ranges"""
    hr = parse_time_range(text)
    if hr is None:
        return None
    return ScheduleIntent(hour_range=hr)
