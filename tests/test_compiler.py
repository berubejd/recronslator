"""Unit tests for the compiler module (ScheduleIntent → CronExpression)."""

import pytest

from recronslator.compiler import compile_intent
from recronslator.model import CronExpression, ScheduleIntent


def compile(intent: ScheduleIntent) -> str:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return str(compile_intent(intent))


class TestMinuteField:
    def test_minute_interval(self) -> None:
        result = compile(ScheduleIntent(minute_interval=15))
        assert result.split()[0] == "*/15"

    def test_minute_range(self) -> None:
        result = compile(ScheduleIntent(minute_range=(0, 14)))
        assert result.split()[0] == "0-14"

    def test_specific_minutes(self) -> None:
        result = compile(ScheduleIntent(minutes=[15, 30, 45]))
        assert result.split()[0] == "15,30,45"

    def test_single_minute(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[3]))
        assert result.split()[0] == "0"

    def test_defaults_to_zero_with_hours(self) -> None:
        result = compile(ScheduleIntent(hours=[3]))
        assert result.split()[0] == "0"

    def test_defaults_to_zero_with_day_constraint(self) -> None:
        result = compile(ScheduleIntent(days_of_week=[1]))
        assert result.split()[0] == "0"

    def test_wildcard_without_constraints(self) -> None:
        result = compile(ScheduleIntent(minute_interval=5, hour_range=(9, 17)))
        assert result.split()[0] == "*/5"


class TestHourField:
    def test_hour_interval(self) -> None:
        result = compile(ScheduleIntent(hour_interval=2))
        assert result.split()[1] == "*/2"

    def test_hour_range(self) -> None:
        result = compile(ScheduleIntent(minute_interval=30, hour_range=(9, 17)))
        assert result.split()[1] == "9-17"

    def test_specific_hours(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[9, 13, 17]))
        assert result.split()[1] == "9,13,17"

    def test_wildcard_with_interval(self) -> None:
        result = compile(ScheduleIntent(minute_interval=15))
        assert result.split()[1] == "*"

    def test_defaults_to_zero_with_day_constraint_no_minutes(self) -> None:
        result = compile(ScheduleIntent(days_of_week=[1]))
        assert result.split()[1] == "0"

    def test_wildcard_when_minutes_set_without_hours(self) -> None:
        # "at :15 past each hour" — minutes=[15], no hour → hour should be "*"
        result = compile(ScheduleIntent(minutes=[15], weekday_only=True))
        assert result.split()[1] == "*"


class TestDayOfMonthField:
    def test_last_day(self) -> None:
        result = compile(ScheduleIntent(last_day_of_month=True, minutes=[0], hours=[0]))
        assert result.split()[2] == "L"

    def test_specific_day(self) -> None:
        result = compile(ScheduleIntent(days_of_month=[15], minutes=[0], hours=[12]))
        assert result.split()[2] == "15"

    def test_first_day(self) -> None:
        result = compile(ScheduleIntent(days_of_month=[1], minutes=[0], hours=[0]))
        assert result.split()[2] == "1"

    def test_day_interval(self) -> None:
        result = compile(ScheduleIntent(day_interval=4, minutes=[0], hours=[12]))
        assert result.split()[2] == "*/4"

    def test_ordinal_weekday_range(self) -> None:
        # first Monday → days 1-7
        result = compile(ScheduleIntent(ordinal_weekday=(1, 1), minutes=[0], hours=[3]))
        assert result.split()[2] == "1-7"

    def test_second_occurrence(self) -> None:
        result = compile(ScheduleIntent(ordinal_weekday=(2, 0), minutes=[0], hours=[0]))
        assert result.split()[2] == "8-14"

    def test_excluded_day(self) -> None:
        result = compile(ScheduleIntent(
            excluded_days_of_month=[13],
            weekday_only=True,
            minutes=[45], hours=[8]
        ))
        assert result.split()[2] == "1-12,14-31"

    def test_first_n_days(self) -> None:
        result = compile(ScheduleIntent(days_of_month=list(range(1, 6)), minutes=[0], hours=[6]))
        assert result.split()[2] == "1-5"


class TestMonthField:
    def test_specific_months(self) -> None:
        result = compile(ScheduleIntent(months=[1, 4, 7, 10], days_of_month=[1], minutes=[0], hours=[0]))
        assert result.split()[3] == "1,4,7,10"

    def test_wildcard_default(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[3], days_of_week=[1]))
        assert result.split()[3] == "*"


class TestDayOfWeekField:
    def test_weekday_only(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[12], weekday_only=True))
        assert result.split()[4] == "1-5"

    def test_weekend_only(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[22], weekend_only=True))
        assert result.split()[4] == "0,6"

    def test_specific_days(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[0], days_of_week=[1, 5]))
        assert result.split()[4] == "1,5"

    def test_ordinal_weekday_dow(self) -> None:
        result = compile(ScheduleIntent(ordinal_weekday=(1, 1), minutes=[0], hours=[3]))
        assert result.split()[4] == "1"

    def test_wildcard_default(self) -> None:
        result = compile(ScheduleIntent(minutes=[0], hours=[3]))
        assert result.split()[4] == "*"


class TestFullExpressions:
    def test_every_monday_3am(self) -> None:
        intent = ScheduleIntent(minutes=[0], hours=[3], days_of_week=[1])
        assert compile(intent) == "0 3 * * 1"

    def test_every_15_minutes(self) -> None:
        assert compile(ScheduleIntent(minute_interval=15)) == "*/15 * * * *"

    def test_business_hours_interval(self) -> None:
        intent = ScheduleIntent(minute_interval=5, hour_range=(9, 17), weekday_only=True)
        assert compile(intent) == "*/5 9-17 * * 1-5"

    def test_last_day_at_midnight(self) -> None:
        intent = ScheduleIntent(last_day_of_month=True, minutes=[59], hours=[23])
        assert compile(intent) == "59 23 L * *"
