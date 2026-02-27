"""Unit tests for the validator module."""

import pytest

from recronslator.model import CronExpression
from recronslator.model import (
    _validate_minute_field,
    _validate_hour_field,
    _validate_dom_field,
    _validate_month_field,
    _validate_dow_field,
)
from recronslator.model import ScheduleIntent
from recronslator.validator import validate_expression, validate_intent


class TestValidateIntent:
    def test_valid_minutes(self) -> None:
        validate_intent(ScheduleIntent(minutes=[0, 30, 59]))

    def test_minute_out_of_range_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minutes=[-1]))

    def test_minute_out_of_range_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minutes=[60]))

    def test_valid_hours(self) -> None:
        validate_intent(ScheduleIntent(minutes=[0], hours=[0, 12, 23]))

    def test_hour_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minutes=[0], hours=[24]))

    def test_minute_interval_valid(self) -> None:
        validate_intent(ScheduleIntent(minute_interval=15))

    def test_minute_interval_too_large(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minute_interval=90))

    def test_minute_interval_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minute_interval=0))

    def test_hour_interval_valid(self) -> None:
        validate_intent(ScheduleIntent(hour_interval=2))

    def test_hour_interval_too_large(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(hour_interval=25))

    def test_day_out_of_range_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(days_of_month=[0], minutes=[0], hours=[0]))

    def test_day_out_of_range_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(days_of_month=[32], minutes=[0], hours=[0]))

    def test_day_of_week_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(days_of_week=[7], minutes=[0], hours=[0]))

    def test_month_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(months=[13], days_of_month=[1], minutes=[0], hours=[0]))

    def test_ordinal_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(ordinal_weekday=(6, 1)))

    def test_weekday_and_weekend_mutual_exclusion(self) -> None:
        with pytest.raises(ValueError, match="cannot both be True"):
            validate_intent(ScheduleIntent(
                weekday_only=True, weekend_only=True, minutes=[0], hours=[0]
            ))

    def test_empty_intent_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_intent(ScheduleIntent())


class TestValidateExpression:
    def test_valid_expression(self) -> None:
        validate_expression(CronExpression("0", "3", "*", "*", "1"))

    def test_invalid_minute_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_expression(CronExpression("60", "*", "*", "*", "*"))

    def test_invalid_hour_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_expression(CronExpression("0", "25", "*", "*", "*"))

    def test_invalid_dom_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_expression(CronExpression("0", "0", "0", "*", "*"))

    def test_invalid_dom_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_expression(CronExpression("0", "0", "32", "*", "*"))

    def test_invalid_month_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_expression(CronExpression("0", "0", "*", "13", "*"))

    def test_invalid_dow_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_expression(CronExpression("0", "0", "*", "*", "7"))

    def test_wildcard_valid(self) -> None:
        validate_expression(CronExpression("*", "*", "*", "*", "*"))

    def test_L_dom_valid(self) -> None:
        validate_expression(CronExpression("59", "23", "L", "*", "*"))

    def test_step_notation_valid(self) -> None:
        validate_expression(CronExpression("*/15", "*", "*", "*", "*"))

    def test_range_notation_valid(self) -> None:
        validate_expression(CronExpression("0", "9-17", "*", "*", "1-5"))

    def test_list_notation_valid(self) -> None:
        validate_expression(CronExpression("0", "9,13,17", "*", "*", "1-5"))


class TestFieldValidators:
    def test_minute_step_valid(self) -> None:
        _validate_minute_field("*/15")
        _validate_minute_field("*/5")

    def test_minute_range_valid(self) -> None:
        _validate_minute_field("0-14")
        _validate_minute_field("30-59")

    def test_minute_list_valid(self) -> None:
        _validate_minute_field("15,30,45")

    def test_hour_step_valid(self) -> None:
        _validate_hour_field("*/2")

    def test_hour_range_valid(self) -> None:
        _validate_hour_field("9-17")

    def test_dom_L_valid(self) -> None:
        _validate_dom_field("L")

    def test_dom_step_valid(self) -> None:
        _validate_dom_field("*/4")

    def test_dow_range_valid(self) -> None:
        _validate_dow_field("1-5")

    def test_dow_list_valid(self) -> None:
        _validate_dow_field("0,6")

    def test_minute_range_step_valid(self) -> None:
        """Step on a non-wildcard base, e.g. '0-14/5' — exercises the value=base fallback."""
        _validate_minute_field("0-14/5")

    def test_hour_range_step_valid(self) -> None:
        """Step on a non-wildcard base for the hour field, e.g. '9-17/2'."""
        _validate_hour_field("9-17/2")

    def test_dom_L_in_list_valid(self) -> None:
        """'L' inside a comma-separated dom list — exercises the part=='L' continue branch."""
        _validate_dom_field("1-15,L")

    def test_dom_range_step_valid(self) -> None:
        """Step on a non-wildcard dom base, e.g. '5/3'."""
        _validate_dom_field("5/3")

    def test_month_range_step_valid(self) -> None:
        """Step on a non-wildcard month base, e.g. '1/3'."""
        _validate_month_field("1/3")


class TestValidateIntentAdditionalBranches:
    def test_ordinal_weekday_weekday_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(ordinal_weekday=(1, 7)))

    def test_hour_range_start_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minute_interval=15, hour_range=(25, 17)))

    def test_hour_range_end_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minute_interval=15, hour_range=(9, 25)))

    def test_minute_range_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(minute_range=(-1, 14)))

    def test_excluded_day_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(excluded_days_of_month=[0], weekday_only=True))

    def test_day_interval_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(day_interval=0))

    def test_hour_interval_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(hour_interval=0))

    def test_excluded_day_of_week_valid(self) -> None:
        validate_intent(ScheduleIntent(weekday_only=True, excluded_days_of_week=[1, 5]))

    def test_excluded_day_of_week_out_of_range_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(weekday_only=True, excluded_days_of_week=[7]))

    def test_excluded_day_of_week_out_of_range_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(weekday_only=True, excluded_days_of_week=[-1]))

    def test_month_interval_valid(self) -> None:
        validate_intent(ScheduleIntent(month_interval=3))

    def test_month_interval_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(month_interval=0))

    def test_month_interval_too_large(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(month_interval=13))

    def test_last_weekday_of_month_valid(self) -> None:
        validate_intent(ScheduleIntent(last_weekday_of_month=5))

    def test_last_weekday_of_month_out_of_range_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(last_weekday_of_month=7))

    def test_last_weekday_of_month_out_of_range_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_intent(ScheduleIntent(last_weekday_of_month=-1))

    def test_ordinal_weekday_valid_nth_and_weekday(self) -> None:
        validate_intent(ScheduleIntent(ordinal_weekday=(2, 3)))


class TestCronExpressionValidateMethod:
    """CronExpression.validate() is a convenience method on the dataclass itself."""

    def test_validate_valid(self) -> None:
        CronExpression("0", "3", "*", "*", "1").validate()

    def test_validate_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            CronExpression("60", "3", "*", "*", "1").validate()


class TestFieldValidatorErrorPaths:
    """Cover every error-raising branch inside the five field validator functions."""

    # ------------------------------------------------------------------
    # _validate_minute_field
    # ------------------------------------------------------------------

    def test_minute_step_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid minute"):
            _validate_minute_field("*/abc")

    def test_minute_step_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_minute_field("*/0")

    def test_minute_range_nonnumeric_endpoint(self) -> None:
        with pytest.raises(ValueError, match="Invalid minute"):
            _validate_minute_field("0-abc")

    def test_minute_range_value_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_minute_field("0-60")

    def test_minute_scalar_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid minute"):
            _validate_minute_field("abc")

    # ------------------------------------------------------------------
    # _validate_hour_field
    # ------------------------------------------------------------------

    def test_hour_step_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid hour"):
            _validate_hour_field("*/abc")

    def test_hour_step_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_hour_field("*/0")

    def test_hour_range_nonnumeric_endpoint(self) -> None:
        with pytest.raises(ValueError, match="Invalid hour"):
            _validate_hour_field("0-abc")

    def test_hour_range_value_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_hour_field("0-24")

    def test_hour_scalar_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid hour"):
            _validate_hour_field("abc")

    # ------------------------------------------------------------------
    # _validate_dom_field
    # ------------------------------------------------------------------

    def test_dom_step_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid day-of-month"):
            _validate_dom_field("*/abc")

    def test_dom_step_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_dom_field("*/0")

    def test_dom_range_nonnumeric_endpoint(self) -> None:
        with pytest.raises(ValueError, match="Invalid day-of-month"):
            _validate_dom_field("1-abc")

    def test_dom_range_value_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_dom_field("1-32")

    def test_dom_scalar_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid day-of-month"):
            _validate_dom_field("abc")

    # ------------------------------------------------------------------
    # _validate_month_field
    # ------------------------------------------------------------------

    def test_month_step_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid month"):
            _validate_month_field("*/abc")

    def test_month_step_zero(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_month_field("*/0")

    def test_month_range_nonnumeric_endpoint(self) -> None:
        with pytest.raises(ValueError, match="Invalid month"):
            _validate_month_field("1-abc")

    def test_month_range_value_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_month_field("1-13")

    def test_month_scalar_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid month"):
            _validate_month_field("abc")

    # ------------------------------------------------------------------
    # _validate_dow_field
    # ------------------------------------------------------------------

    def test_dow_range_nonnumeric_endpoint(self) -> None:
        with pytest.raises(ValueError, match="Invalid day-of-week"):
            _validate_dow_field("0-abc")

    def test_dow_range_value_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            _validate_dow_field("0-7")

    def test_dow_scalar_nonnumeric(self) -> None:
        with pytest.raises(ValueError, match="Invalid day-of-week"):
            _validate_dow_field("abc")
