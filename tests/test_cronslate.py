"""Integration tests: full English → cron pipeline."""

import warnings

import pytest

import recronslator


def cronslate(text: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return recronslator.cronslate(text)


class TestIntervals:
    def test_every_minute_bare(self) -> None:
        """Bug regression: 'every minute' raised ValueError."""
        assert cronslate("every minute") == "* * * * *"

    def test_every_minute(self) -> None:
        assert cronslate("every 1 minute") == "* * * * *"

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

    def test_interval_with_from_to_range(self) -> None:
        """Bug regression: 'from X to Y' was not recognised as a time range."""
        assert cronslate("every 20 minutes from 1pm to 4pm on fridays") == "*/20 13-16 * * 5"

    def test_interval_with_from_to_range_no_day(self) -> None:
        assert cronslate("every 15 minutes from 9am to 5pm") == "*/15 9-17 * * *"

    def test_interval_with_from_to_range_on_weekdays(self) -> None:
        assert cronslate("every 30 minutes from 9am to 5pm on weekdays") == "*/30 9-17 * * 1-5"

    def test_interval_short_meridiem_from_to(self) -> None:
        """Bug regression: '1p'/'4p' shorthand was silently dropping the hour range."""
        assert cronslate("every 5 minutes from 1p to 4p on fridays") == "*/5 13-16 * * 5"

    def test_interval_short_meridiem_between_and(self) -> None:
        assert cronslate("every 30 minutes between 9a and 5p on weekdays") == "*/30 9-17 * * 1-5"


class TestHourlyRanged:
    def test_every_hour_between_am_pm(self) -> None:
        assert cronslate("every hour between 9am and 5pm") == "0 9-17 * * *"

    def test_every_hour_between_on_weekdays(self) -> None:
        assert cronslate("every hour between 9am and 5pm on weekdays") == "0 9-17 * * 1-5"

    def test_hourly_between(self) -> None:
        assert cronslate("hourly between 9am and 5pm") == "0 9-17 * * *"

    def test_every_hour_from_to(self) -> None:
        assert cronslate("every hour from 8am to 6pm") == "0 8-18 * * *"

    def test_every_hour_short_meridiem(self) -> None:
        """Bug regression: hour range with short meridiem was silently dropped."""
        assert cronslate("every hour between 9a and 5p on weekdays") == "0 9-17 * * 1-5"

    def test_every_hour_no_range_unaffected(self) -> None:
        assert cronslate("every hour") == "0 * * * *"

    def test_hourly_no_range_unaffected(self) -> None:
        assert cronslate("hourly") == "0 * * * *"


class TestShortMeridiem:
    """Short-form am/pm suffixes ('a'/'p') accepted everywhere full forms are."""

    def test_at_3p(self) -> None:
        assert cronslate("every monday at 3p") == "0 15 * * 1"

    def test_at_9a(self) -> None:
        assert cronslate("every weekday at 9a") == "0 9 * * 1-5"

    def test_from_to_short(self) -> None:
        assert cronslate("every 20 minutes from 1p to 4p") == "*/20 13-16 * * *"

    def test_between_and_short(self) -> None:
        assert cronslate("every 15 minutes between 9a and 5p") == "*/15 9-17 * * *"


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

    def test_quarter_after(self) -> None:
        assert cronslate("every hour at quarter after") == "15 * * * *"

    def test_quarter_after_weekdays(self) -> None:
        assert cronslate("at quarter after on weekdays") == "15 * * * 1-5"

    def test_quarter_to(self) -> None:
        assert cronslate("every hour at quarter to") == "45 * * * *"

    def test_quarter_till_weekdays(self) -> None:
        assert cronslate("at quarter till on weekdays") == "45 * * * 1-5"

    def test_quarter_of(self) -> None:
        assert cronslate("at quarter of each hour") == "45 * * * *"

    def test_on_the_hour(self) -> None:
        assert cronslate("on the hour") == "0 * * * *"

    def test_top_of_the_hour(self) -> None:
        assert cronslate("top of the hour") == "0 * * * *"

    def test_on_the_hour_with_range(self) -> None:
        assert cronslate("on the hour between 9am and 5pm") == "0 9-17 * * *"

    def test_on_the_hour_weekdays(self) -> None:
        assert cronslate("every weekday on the hour") == "0 * * * 1-5"


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


class TestDayRanges:
    """Bug regression: 'through' was only capturing first and last day."""

    def test_monday_through_friday(self) -> None:
        assert cronslate("monday through friday at 9am") == "0 9 * * 1-5"

    def test_monday_through_wednesday(self) -> None:
        assert cronslate("monday through wednesday at noon") == "0 12 * * 1-3"

    def test_friday_through_sunday(self) -> None:
        result = cronslate("friday through sunday at midnight")
        assert result == "0 0 * * 0,5-6"

    def test_monday_thru_friday(self) -> None:
        assert cronslate("monday thru friday at 9am") == "0 9 * * 1-5"


class TestMultipleTimes:
    """Bug regression: only the first/special time was captured in mixed lists."""

    def test_three_times_a_day(self) -> None:
        assert cronslate("three times a day at 8am, noon, and 6pm") == "0 8,12,18 * * *"

    def test_at_noon_and_6pm(self) -> None:
        assert cronslate("at noon and 6pm on weekdays") == "0 12,18 * * 1-5"

    def test_at_8am_noon_5pm_weekdays(self) -> None:
        assert cronslate("at 8am, noon, and 5pm on weekdays") == "0 8,12,17 * * 1-5"


class TestMultipleDom:
    """Bug regression: only the first ordinal DOM was captured."""

    def test_twice_a_month(self) -> None:
        assert cronslate("twice a month on the 1st and 15th") == "0 0 1,15 * *"

    def test_three_dom_values(self) -> None:
        result = cronslate("on the 1st, 10th, and 20th of the month at 9am")
        assert result == "0 9 1,10,20 * *"


class TestMonthlyShorthand:
    def test_monthly(self) -> None:
        assert cronslate("monthly") == "0 0 1 * *"

    def test_monthly_with_time(self) -> None:
        assert cronslate("monthly at 9am") == "0 9 1 * *"

    def test_monthly_with_explicit_day(self) -> None:
        assert cronslate("monthly on the 15th at noon") == "0 12 15 * *"

    def test_every_month(self) -> None:
        assert cronslate("every month at noon") == "0 12 1 * *"

    def test_quarterly(self) -> None:
        assert cronslate("quarterly") == "0 0 1 1,4,7,10 *"

    def test_quarterly_with_time(self) -> None:
        assert cronslate("quarterly at 9am") == "0 9 1 1,4,7,10 *"

    def test_quarterly_with_explicit_day(self) -> None:
        assert cronslate("quarterly on the 15th") == "0 0 15 1,4,7,10 *"


class TestMonthIntervals:
    def test_every_other_month(self) -> None:
        assert cronslate("every other month") == "0 0 * */2 *"

    def test_every_3_months(self) -> None:
        assert cronslate("every 3 months") == "0 0 * */3 *"

    def test_every_3_months_on_first(self) -> None:
        assert cronslate("every 3 months on the first at 9am") == "0 9 1 */3 *"

    def test_every_other_day(self) -> None:
        assert cronslate("every other day") == "0 0 */2 * *"


class TestLastWeekday:
    """'last Friday of the month' should produce NL notation."""

    def test_last_friday(self) -> None:
        assert cronslate("last friday of the month at 9am") == "0 9 * * 5L"

    def test_last_monday(self) -> None:
        assert cronslate("last monday of the month") == "0 0 * * 1L"

    def test_last_sunday_at_noon(self) -> None:
        assert cronslate("last sunday at noon") == "0 12 * * 0L"

    def test_last_wednesday_afternoon(self) -> None:
        assert cronslate("last wednesday of the month at 3pm") == "0 15 * * 3L"


class TestDowExceptions:
    """Bug regression: exception day was being included, not excluded."""

    def test_every_day_except_monday(self) -> None:
        result = cronslate("every day except monday")
        assert result == "0 0 * * 0,2-6"

    def test_every_day_except_friday(self) -> None:
        result = cronslate("every day except friday")
        assert result == "0 0 * * 0-4,6"

    def test_every_day_except_sunday(self) -> None:
        result = cronslate("every day except sunday")
        assert result == "0 0 * * 1-6"

    def test_every_day_except_weekends(self) -> None:
        """Bug regression: 'except weekends' was returning weekends only."""
        result = cronslate("every day except weekends")
        assert result == "0 0 * * 1-5"

    def test_except_day_with_time(self) -> None:
        result = cronslate("every day except monday at 9am")
        assert result == "0 9 * * 0,2-6"


class TestCaseInsensitivity:
    def test_uppercase(self) -> None:
        assert cronslate("EVERY MONDAY AT 3AM") == "0 3 * * 1"

    def test_mixed_case(self) -> None:
        assert cronslate("every SUNDAY at 4:30 pm") == "30 16 * * 0"
