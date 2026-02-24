"""Integration tests: full English → cron pipeline."""

import warnings

import pytest

import recronslator


def cronslate(text: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return recronslator.cronslate(text)


class TestIntervals:
    def test_every_minute(self) -> None:
        assert cronslate("every 1 minute") == "*/1 * * * *"

    def test_every_5_minutes(self) -> None:
        assert cronslate("every 5 minutes") == "*/5 * * * *"

    def test_every_15_minutes(self) -> None:
        assert cronslate("every 15 minutes") == "*/15 * * * *"

    def test_every_30_minutes(self) -> None:
        assert cronslate("every 30 minutes") == "*/30 * * * *"

    def test_every_2_hours(self) -> None:
        assert cronslate("every 2 hours") == "0 */2 * * *"

    def test_every_hour(self) -> None:
        assert cronslate("every hour") == "0 * * * *"

    def test_hourly(self) -> None:
        assert cronslate("hourly") == "0 * * * *"

    def test_interval_with_range_and_weekday(self) -> None:
        assert cronslate("every 5 minutes during business hours") == "*/5 9-17 * * 1-5"


class TestShorthands:
    def test_daily(self) -> None:
        assert cronslate("daily") == "0 0 * * *"

    def test_every_day(self) -> None:
        assert cronslate("every day") == "0 0 * * *"

    def test_weekly_on_monday(self) -> None:
        result = cronslate("weekly on monday")
        assert result == "0 0 * * 1"

    def test_half_hour(self) -> None:
        assert cronslate("every hour on the half hour") == "30 * * * *"

    def test_quarter_hour(self) -> None:
        assert cronslate("every quarter hour") == "*/15 * * * *"

    def test_quarter_hour_with_range(self) -> None:
        assert cronslate("every quarter hour between 2pm and 6pm") == "*/15 14-18 * * *"

    def test_quarter_past(self) -> None:
        assert cronslate("weekdays at quarter past each hour") == "15 * * * 1-5"


class TestSpecificTimes:
    def test_at_3am(self) -> None:
        assert cronslate("every monday at 3am") == "0 3 * * 1"

    def test_at_4_30_pm(self) -> None:
        assert cronslate("every sunday at 4:30 pm") == "30 16 * * 0"

    def test_at_noon(self) -> None:
        assert cronslate("every weekday at noon") == "0 12 * * 1-5"

    def test_at_midnight(self) -> None:
        assert cronslate("first day of every month at midnight") == "0 0 1 * *"

    def test_multiple_times(self) -> None:
        assert cronslate("every weekday at 9am, 1pm and 5pm") == "0 9,13,17 * * 1-5"

    def test_twice_daily(self) -> None:
        assert cronslate("twice daily at 6:30 and 18:30") == "30 6,18 * * *"

    def test_three_times_per_hour(self) -> None:
        assert cronslate("three times per hour at 15, 30, and 45 minutes") == "15,30,45 * * * *"


class TestDayOfWeek:
    def test_weekdays(self) -> None:
        assert cronslate("every 30 minutes between 9am and 5pm on weekdays") == "*/30 9-17 * * 1-5"

    def test_weekends(self) -> None:
        assert cronslate("every weekend at 10pm") == "0 22 * * 0,6"

    def test_multiple_named_days(self) -> None:
        assert cronslate("at midnight on mondays and fridays") == "0 0 * * 1,5"

    def test_workday_except(self) -> None:
        assert cronslate("workdays at 8:45 am except on the 13th") == "45 8 1-12,14-31 * 1-5"


class TestDayOfMonth:
    def test_first_day(self) -> None:
        assert cronslate("first day of every month at midnight") == "0 0 1 * *"

    def test_specific_day(self) -> None:
        assert cronslate("monthly on the 15th at noon") == "0 12 15 * *"

    def test_last_day(self) -> None:
        assert cronslate("last day of month at 11:59 pm") == "59 23 L * *"

    def test_ordinal_weekday(self) -> None:
        assert cronslate("first monday of every month at 3am") == "0 3 1-7 * 1"

    def test_second_ordinal_weekday(self) -> None:
        assert cronslate("second monday of every month at midnight") == "0 0 8-14 * 1"

    def test_day_interval(self) -> None:
        assert cronslate("every fourth day at noon") == "0 12 */4 * *"

    def test_first_n_days(self) -> None:
        assert cronslate("first 5 days of each quarter at dawn") == "0 6 1-5 1,4,7,10 *"


class TestInexpressibleSchedules:
    def test_biweekly(self) -> None:
        with pytest.raises(ValueError, match="[Bb]iweekly"):
            cronslate("biweekly on monday")

    def test_every_other_week(self) -> None:
        with pytest.raises(ValueError):
            cronslate("every other week on friday")

    def test_bimonthly(self) -> None:
        with pytest.raises(ValueError, match="[Bb]imonthly"):
            cronslate("bimonthly on the 1st")

    def test_minute_interval_90(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            cronslate("every 90 minutes")

    def test_hour_25(self) -> None:
        with pytest.raises(ValueError):
            cronslate("at 25:00")

    def test_day_32(self) -> None:
        with pytest.raises(ValueError):
            cronslate("on day 32 of the month")


class TestCaseInsensitivity:
    def test_uppercase(self) -> None:
        assert cronslate("EVERY MONDAY AT 3AM") == "0 3 * * 1"

    def test_mixed_case(self) -> None:
        assert cronslate("every SUNDAY at 4:30 pm") == "30 16 * * 0"
