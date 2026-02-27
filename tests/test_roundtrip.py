"""Roundtrip tests: forward pipeline correctness, describe quality, and stability.

Three complementary test layers:
1. test_forward_and_describe_keywords  — English → cron is correct AND the
   description contains the expected semantic tokens.
2. test_cron_to_english_to_cron_stable — cron → English → cron produces the
   identical cron expression (full stability).
3. TestKnownLimitations                — expressions whose descriptions are
   correct but cannot re-parse back to the identical cron due to known parser
   gaps.  Kept here so regressions surface immediately.
"""

import warnings

import pytest

import recronslator


def cronslate(text: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return recronslator.cronslate(text)


# ---------------------------------------------------------------------------
# Layer 1 — Forward correctness + description keyword checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "description,expected_cron,expected_keywords",
    [
        ("Every Monday at 3am",
         "0 3 * * 1",
         ["3:00 AM", "Monday"]),

        ("Every weekday at noon",
         "0 12 * * 1-5",
         ["noon", "weekday"]),

        ("Every 15 minutes",
         "*/15 * * * *",
         ["15"]),

        ("First day of every month at midnight",
         "0 0 1 * *",
         ["midnight", "1st"]),

        ("Every Sunday at 4:30 PM",
         "30 16 * * 0",
         ["4:30 PM", "Sunday"]),

        ("Every hour on the half hour",
         "30 * * * *",
         [":30"]),

        ("Every day at 2am and 2pm",
         "0 2,14 * * *",
         ["2:00 AM", "2:00 PM"]),

        ("Every 30 minutes between 9am and 5pm on weekdays",
         "*/30 9-17 * * 1-5",
         ["30", "9:00 AM", "5:00 PM", "weekday"]),

        ("First Monday of every month at 3am",
         "0 3 1-7 * 1",
         ["3:00 AM", "first", "Monday"]),

        ("Every quarter hour between 2pm and 6pm",
         "*/15 14-18 * * *",
         ["15", "2:00 PM", "6:00 PM"]),

        ("Every weekend at 10pm",
         "0 22 * * 0,6",
         ["10:00 PM", "weekend"]),

        ("Every 5 minutes during business hours",
         "*/5 9-17 * * 1-5",
         ["5", "9:00 AM", "5:00 PM", "weekday"]),

        ("3rd day of every month at 1:30am",
         "30 1 3 * *",
         ["1:30 AM", "3rd"]),

        ("Every weekday at 9am, 1pm and 5pm",
         "0 9,13,17 * * 1-5",
         ["9:00 AM", "1:00 PM", "5:00 PM", "weekday"]),

        ("At midnight on Mondays and Fridays",
         "0 0 * * 1,5",
         ["midnight", "Monday", "Friday"]),

        ("Twice daily at 6:30 and 18:30",
         "30 6,18 * * *",
         ["6:30 AM", "6:30 PM"]),

        ("Monthly on the 15th at noon",
         "0 12 15 * *",
         ["noon", "15th"]),

        ("Three times per hour at 15, 30, and 45 minutes",
         "15,30,45 * * * *",
         [":15", ":30", ":45"]),

        ("Last day of month at 11:59 PM",
         "59 23 L * *",
         ["11:59 PM", "last"]),

        ("Weekdays at quarter past each hour",
         "15 * * * 1-5",
         [":15", "weekday"]),

        ("Once per hour in the first 15 minutes",
         "0-14 * * * *",
         ["15"]),

        ("Workdays at 8:45 AM except on the 13th",
         "45 8 1-12,14-31 * 1-5",
         ["8:45 AM", "13", "weekday"]),

        ("First 5 days of each quarter at dawn",
         "0 6 1-5 1,4,7,10 *",
         ["6:00 AM", "quarter"]),

        # --- features added this session ---
        ("Every minute",
         "* * * * *",
         ["minute"]),

        ("Every 20 minutes from 1pm to 4pm on fridays",
         "*/20 13-16 * * 5",
         ["20", "1:00 PM", "4:00 PM", "Friday"]),

        ("Every 15 minutes from 9am to 5pm",
         "*/15 9-17 * * *",
         ["15", "9:00 AM", "5:00 PM"]),

        ("Every hour between 9am and 5pm",
         "0 9-17 * * *",
         ["hour", "9:00 AM", "5:00 PM"]),

        ("Every hour between 9am and 5pm on weekdays",
         "0 9-17 * * 1-5",
         ["hour", "9:00 AM", "5:00 PM", "weekday"]),

        # --- colloquial minute expressions added this session ---
        ("Every hour at quarter after",
         "15 * * * *",
         [":15"]),

        ("At quarter after on weekdays",
         "15 * * * 1-5",
         [":15", "weekday"]),

        ("Every hour at quarter to",
         "45 * * * *",
         [":45"]),

        ("At quarter till on weekdays",
         "45 * * * 1-5",
         [":45", "weekday"]),

        ("At quarter of each hour",
         "45 * * * *",
         [":45"]),

        ("On the hour",
         "0 * * * *",
         [":00"]),

        ("On the hour between 9am and 5pm",
         "0 9-17 * * *",
         ["9:00 AM", "5:00 PM"]),

        ("Every weekday on the hour",
         "0 * * * 1-5",
         [":00", "weekday"]),

        # --- Phase 1-5 bug fixes ---
        ("Monday through friday at 9am",
         "0 9 * * 1-5",
         ["9:00 AM", "weekday"]),

        ("Three times a day at 8am, noon, and 6pm",
         "0 8,12,18 * * *",
         ["8:00 AM", "12:00 PM", "6:00 PM"]),

        ("Twice a month on the 1st and 15th",
         "0 0 1,15 * *",
         ["1st", "15th"]),

        ("Every day except monday",
         "0 0 * * 0,2-6",
         ["midnight"]),

        ("Every day except weekends",
         "0 0 * * 1-5",
         ["weekday"]),

        ("Monthly",
         "0 0 1 * *",
         ["midnight", "1st"]),

        ("Quarterly",
         "0 0 1 1,4,7,10 *",
         ["1st", "quarter"]),

        ("Every other day",
         "0 0 */2 * *",
         ["2 day"]),

        ("Every other month",
         "0 0 * */2 *",
         ["every other month"]),

        ("Last friday of the month at 9am",
         "0 9 * * 5L",
         ["last Friday", "9:00 AM"]),

        # --- every-minute ranged (PR fix) ---
        ("Every minute from 9am to 5pm",
         "* 9-17 * * *",
         ["minute", "9:00 AM", "5:00 PM"]),

        ("Every minute between 9am and 5pm on weekdays",
         "* 9-17 * * 1-5",
         ["minute", "9:00 AM", "5:00 PM", "weekday"]),

        # --- Oxford-comma multi-time fix ---
        ("At 3pm, 4pm, and 6pm",
         "0 15,16,18 * * *",
         ["3:00 PM", "4:00 PM", "6:00 PM"]),
    ],
)
def test_forward_and_describe_keywords(
    description: str, expected_cron: str, expected_keywords: list[str]
) -> None:
    """cronslate produces the correct cron AND describe contains expected tokens."""
    cron = cronslate(description)
    assert cron == expected_cron

    english = recronslator.describe(cron)
    assert isinstance(english, str) and len(english) > 0

    english_lower = english.lower()
    for kw in expected_keywords:
        assert kw.lower() in english_lower, (
            f"Expected token {kw!r} in describe({cron!r}), got {english!r}"
        )


# ---------------------------------------------------------------------------
# Layer 2 — Full cron → English → cron stability (identical round-trip)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cron",
    [
        # Core schedules
        "0 3 * * 1",           # specific time + weekday
        "0 12 * * 1-5",        # noon on weekdays
        "*/15 * * * *",        # minute interval
        "0 0 1 * *",           # first of month at midnight
        "30 16 * * 0",         # specific time on specific day
        "*/30 9-17 * * 1-5",   # interval with hour range + weekday
        "0 3 1-7 * 1",         # ordinal weekday
        "*/15 14-18 * * *",    # interval with hour range
        "0 22 * * 0,6",        # weekends
        "*/5 9-17 * * 1-5",    # business hours interval
        "30 1 3 * *",          # specific day of month
        "0 0 * * 1,5",         # multiple named days
        "0 12 15 * *",         # specific dom at noon
        "59 23 L * *",         # last day of month
        "0-14 * * * *",        # minute range
        "45 8 1-12,14-31 * 1-5",  # exception day pattern
        # Features added this session
        "* * * * *",           # every minute
        "*/20 13-16 * * 5",    # from/to range on a day
        "*/15 15 * * *",       # interval at specific single hour
        "*/15 15 * * 3",       # interval at specific hour on specific day
        "0 9-17 * * *",        # hourly with range
        "0 9-17 * * 1-5",      # hourly with range on weekdays
        "0 8-18 * * *",        # hourly with range (wider window)
        # Describer + parser fixes (previously Layer 3)
        "30 * * * *",          # :N past every hour
        "15 * * * 1-5",        # :N past every hour on weekdays
        "0 2,14 * * *",        # two colon-format times
        "0 9,13,17 * * 1-5",   # three colon-format times on weekdays
        "30 6,18 * * *",       # colon-format times with non-zero minute
        "* 9-17 * * *",        # every minute with hour range
        "* 9-17 * * 3",        # every minute with hour range + specific dow
        "* 9-17 * * 1-5",      # every minute with hour range on weekdays
    ],
)
def test_cron_to_english_to_cron_stable(cron: str) -> None:
    """cron → describe → cronslate must reproduce the original expression."""
    english = recronslator.describe(cron)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        recron = recronslator.cronslate(english)
    assert recron == cron, (
        f"describe({cron!r}) = {english!r}\n"
        f"cronslate({english!r}) = {recron!r}"
    )


# ---------------------------------------------------------------------------
# Layer 3 — Known limitations (descriptions are correct but not re-parseable)
# ---------------------------------------------------------------------------

class TestKnownLimitations:
    """These cron expressions produce correct descriptions but cannot round-trip
    back to the same cron.  Tests assert the *current* (imperfect) re-parse
    result so any regression is immediately visible.

    Root causes are documented inline.
    """

    def test_first_n_days_of_quarter(self) -> None:
        # '0 6 1-5 1,4,7,10 *' → 'At 6:00 AM on days 1-5 of the month each quarter'
        # "on days 1-5" is not a recognised parser phrase; only the quarter
        # months are recovered.
        english = recronslator.describe("0 6 1-5 1,4,7,10 *")
        assert "6:00 AM" in english and "quarter" in english.lower()
        assert cronslate(english) == "0 6 * 1,4,7,10 *"  # loses dom range

