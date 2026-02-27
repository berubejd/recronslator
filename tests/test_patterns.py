"""Unit tests for individual pattern functions in the pattern registry."""

import pytest

from recronslator.parsing.patterns import parse
from recronslator.model import ScheduleIntent


def p(text: str) -> ScheduleIntent:
    """Convenience: parse normalized text and return ScheduleIntent."""
    return parse(text.lower())


class TestIntervalPatterns:
    def test_every_15_minutes(self) -> None:
        intent = p("every 15 minutes")
        assert intent.minute_interval == 15

    def test_every_minute_bare(self) -> None:
        """Bug regression: 'every minute' raised ValueError."""
        intent = p("every minute")
        assert intent.minute_interval == 1

    def test_every_30_minutes_between(self) -> None:
        intent = p("every 30 minutes between 9am and 5pm on weekdays")
        assert intent.minute_interval == 30
        assert intent.hour_range == (9, 17)
        assert intent.weekday_only is True

    def test_every_20_minutes_from_to(self) -> None:
        """Bug regression: 'from X to Y' syntax was not recognised."""
        intent = p("every 20 minutes from 1pm to 4pm on fridays")
        assert intent.minute_interval == 20
        assert intent.hour_range == (13, 16)

    def test_every_15_minutes_from_to_no_day(self) -> None:
        intent = p("every 15 minutes from 9am to 5pm")
        assert intent.minute_interval == 15
        assert intent.hour_range == (9, 17)

    def test_every_2_hours(self) -> None:
        intent = p("every 2 hours")
        assert intent.hour_interval == 2

    def test_every_5_minutes_business_hours(self) -> None:
        intent = p("every 5 minutes during business hours")
        assert intent.minute_interval == 5
        assert intent.hour_range == (9, 17)
        assert intent.weekday_only is True

    def test_minute_interval_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            p("every 90 minutes")


class TestShorthandPatterns:
    def test_every_hour(self) -> None:
        intent = p("every hour")
        assert intent.minutes == [0]

    def test_hourly(self) -> None:
        intent = p("hourly")
        assert intent.minutes == [0]

    def test_every_day(self) -> None:
        intent = p("every day")
        assert intent.minutes == [0]
        assert intent.hours == [0]

    def test_half_hour(self) -> None:
        intent = p("every hour on the half hour")
        assert intent.minutes == [30]

    def test_quarter_hour(self) -> None:
        intent = p("every quarter hour")
        assert intent.minute_interval == 15

    def test_quarter_past(self) -> None:
        intent = p("weekdays at quarter past each hour")
        assert intent.minutes == [15]
        assert intent.weekday_only is True

    def test_quarter_after(self) -> None:
        intent = p("at quarter after on weekdays")
        assert intent.minutes == [15]
        assert intent.weekday_only is True

    def test_quarter_after_no_weekday(self) -> None:
        intent = p("every hour at quarter after")
        assert intent.minutes == [15]

    def test_quarter_to(self) -> None:
        intent = p("at quarter to each hour")
        assert intent.minutes == [45]
        assert not intent.weekday_only

    def test_quarter_till_weekdays(self) -> None:
        intent = p("at quarter till on weekdays")
        assert intent.minutes == [45]
        assert intent.weekday_only is True

    def test_quarter_of(self) -> None:
        intent = p("at quarter of each hour")
        assert intent.minutes == [45]

    def test_on_the_hour(self) -> None:
        intent = p("on the hour")
        assert intent.minutes == [0]

    def test_top_of_the_hour(self) -> None:
        intent = p("top of the hour")
        assert intent.minutes == [0]

    def test_on_the_hour_with_range(self) -> None:
        intent = p("on the hour between 9am and 5pm")
        assert intent.minutes == [0]
        assert intent.hour_range == (9, 17)

    def test_on_the_hour_weekdays(self) -> None:
        intent = p("every weekday on the hour")
        assert intent.minutes == [0]


class TestTimeEnrichers:
    def test_at_3am(self) -> None:
        intent = p("every monday at 3am")
        assert intent.hours == [3]
        assert intent.minutes == [0]

    def test_at_4_30_pm(self) -> None:
        intent = p("every sunday at 4:30 pm")
        assert intent.hours == [16]
        assert intent.minutes == [30]

    def test_at_midnight(self) -> None:
        intent = p("first day of every month at midnight")
        assert intent.hours == [0]
        assert intent.minutes == [0]

    def test_multiple_times(self) -> None:
        intent = p("every weekday at 9am, 1pm and 5pm")
        assert intent.hours == [9, 13, 17]
        assert intent.minutes == [0]

    def test_first_n_minutes(self) -> None:
        intent = p("once per hour in the first 15 minutes")
        assert intent.minute_range == (0, 14)

    def test_times_per_hour(self) -> None:
        intent = p("3 times per hour at 15, 30, and 45 minutes")
        assert intent.minutes == [15, 30, 45]


class TestDayOfWeekEnrichers:
    def test_weekday_constraint(self) -> None:
        intent = p("every 30 minutes between 9am and 5pm on weekdays")
        assert intent.weekday_only is True

    def test_weekend_constraint(self) -> None:
        intent = p("every weekend at 10pm")
        assert intent.weekend_only is True

    def test_named_days(self) -> None:
        intent = p("at midnight on mondays and fridays")
        assert 1 in (intent.days_of_week or [])
        assert 5 in (intent.days_of_week or [])

    def test_named_days_singular(self) -> None:
        intent = p("every monday at 3am")
        assert intent.days_of_week == [1]


class TestDayOfMonthEnrichers:
    def test_ordinal_weekday(self) -> None:
        intent = p("first monday of every month at 3am")
        assert intent.ordinal_weekday == (1, 1)

    def test_second_occurrence(self) -> None:
        intent = p("every second sunday")
        assert intent.ordinal_weekday == (2, 0)

    def test_last_day(self) -> None:
        intent = p("last day of month at 11:59 pm")
        assert intent.last_day_of_month is True

    def test_specific_day(self) -> None:
        intent = p("monthly on the 15th at noon")
        assert intent.days_of_month == [15]

    def test_day_exception(self) -> None:
        intent = p("workdays at 8:45 am except on the 13th")
        assert intent.excluded_days_of_month == [13]
        assert intent.weekday_only is True

    def test_first_n_days(self) -> None:
        intent = p("first 5 days of each quarter at dawn")
        assert intent.days_of_month == [1, 2, 3, 4, 5]


class TestMonthEnrichers:
    def test_quarter_months(self) -> None:
        intent = p("first 5 days of each quarter at dawn")
        assert intent.months == [1, 4, 7, 10]

    def test_quarter_hours_does_not_set_months(self) -> None:
        intent = p("every quarter hour between 2pm and 6pm")
        assert intent.months is None


class TestInvalidInputs:
    def test_invalid_hour_raises(self) -> None:
        with pytest.raises(ValueError):
            p("at 25:00")

    def test_invalid_day_raises(self) -> None:
        with pytest.raises(ValueError):
            p("on day 32")

    def test_empty_intent_raises(self) -> None:
        with pytest.raises(ValueError, match="Could not understand"):
            p("invalid cron string")
