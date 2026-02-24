"""Unit tests for the describer module (CronExpression → English)."""

import pytest

from recronslator.describer import describe


class TestIntervalDescriptions:
    def test_every_15_minutes(self) -> None:
        assert describe("*/15 * * * *") == "Every 15 minutes"

    def test_every_5_minutes(self) -> None:
        assert describe("*/5 * * * *") == "Every 5 minutes"

    def test_every_minute(self) -> None:
        assert describe("*/1 * * * *") == "Every 1 minute"

    def test_every_30_minutes_with_range(self) -> None:
        result = describe("*/30 9-17 * * 1-5")
        assert "30 minutes" in result
        assert "9:00 AM" in result
        assert "5:00 PM" in result

    def test_every_2_hours(self) -> None:
        assert describe("0 */2 * * *") == "Every 2 hours"


class TestSpecificTimeDescriptions:
    def test_monday_3am(self) -> None:
        result = describe("0 3 * * 1")
        assert "3:00 AM" in result
        assert "Monday" in result

    def test_midnight(self) -> None:
        result = describe("0 0 * * *")
        assert "midnight" in result.lower() or "12:00 AM" in result

    def test_noon(self) -> None:
        result = describe("0 12 * * *")
        assert "noon" in result.lower() or "12:00 PM" in result

    def test_4_30_pm(self) -> None:
        result = describe("30 16 * * 0")
        assert "4:30 PM" in result
        assert "Sunday" in result

    def test_multiple_hours(self) -> None:
        result = describe("0 9,13,17 * * 1-5")
        assert "9:00 AM" in result
        assert "1:00 PM" in result
        assert "5:00 PM" in result


class TestDayDescriptions:
    def test_weekdays(self) -> None:
        result = describe("0 12 * * 1-5")
        assert "weekday" in result.lower()

    def test_weekends(self) -> None:
        result = describe("0 22 * * 0,6")
        assert "weekend" in result.lower()

    def test_specific_day(self) -> None:
        result = describe("0 3 * * 1")
        assert "Monday" in result

    def test_multiple_days(self) -> None:
        result = describe("0 0 * * 1,5")
        assert "Monday" in result
        assert "Friday" in result

    def test_first_day_of_month(self) -> None:
        result = describe("0 0 1 * *")
        assert "1st" in result or "first" in result.lower()

    def test_last_day_of_month(self) -> None:
        result = describe("59 23 L * *")
        assert "last" in result.lower()

    def test_ordinal_weekday(self) -> None:
        result = describe("0 3 1-7 * 1")
        assert "first" in result.lower() or "1st" in result
        assert "Monday" in result

    def test_day_interval(self) -> None:
        result = describe("0 12 */4 * *")
        assert "4" in result


class TestMonthDescriptions:
    def test_quarter_months(self) -> None:
        result = describe("0 6 1-5 1,4,7,10 *")
        assert "quarter" in result.lower() or "January" in result

    def test_specific_month(self) -> None:
        result = describe("0 0 1 3 *")
        assert "March" in result


class TestMinuteRangeDescriptions:
    def test_first_15_minutes(self) -> None:
        result = describe("0-14 * * * *")
        assert "15" in result or "first" in result.lower()


class TestInvalidExpressions:
    def test_wrong_field_count(self) -> None:
        with pytest.raises(ValueError, match="5-field"):
            describe("0 3 * *")

    def test_invalid_hour(self) -> None:
        with pytest.raises(ValueError):
            describe("0 25 * * *")

    def test_invalid_minute(self) -> None:
        with pytest.raises(ValueError):
            describe("60 0 * * *")

    def test_invalid_dom(self) -> None:
        with pytest.raises(ValueError):
            describe("0 0 32 * *")

    def test_invalid_month(self) -> None:
        with pytest.raises(ValueError):
            describe("0 0 * 13 *")

    def test_invalid_dow(self) -> None:
        with pytest.raises(ValueError):
            describe("0 0 * * 7")


class TestReturnType:
    def test_returns_string(self) -> None:
        result = describe("0 3 * * 1")
        assert isinstance(result, str)

    def test_returns_nonempty(self) -> None:
        result = describe("*/15 * * * *")
        assert len(result) > 0


class TestUncoveredDescriberBranches:
    def test_specific_minute_wildcard_hour(self) -> None:
        """Minute is specific but hour is wildcard → 'At :MM past every hour'."""
        result = describe("15 * * * *")
        assert ":15" in result

    def test_multiple_different_minutes_with_hour(self) -> None:
        """Multiple distinct minute values with a specific hour."""
        result = describe("15,30 9 * * *")
        assert "9" in result

    def test_minute_interval_specific_hour(self) -> None:
        """Minute interval combined with a single non-range hour → fallback in _describe_hour_constraint."""
        result = describe("*/30 3 * * *")
        assert "30" in result
        assert "3" in result

    def test_dom_multiple_excluded_days(self) -> None:
        """dom with comma-separated ranges where multiple days are excluded → 'on days ... of the month'."""
        result = describe("0 0 1-10,15-31 * *")
        assert "day" in result.lower()

    def test_dom_step_from_nonwildcard_base(self) -> None:
        """dom step with a non-wildcard base like '5/3' → final fallback 'on day ...'."""
        result = describe("0 0 5/3 * *")
        assert "5/3" in result or "day" in result.lower()

    def test_month_step_pattern(self) -> None:
        """Step pattern in month field → 'in month ...' fallback."""
        result = describe("0 0 1 */3 *")
        assert "month" in result.lower() or "*/3" in result

    def test_two_months(self) -> None:
        """Exactly two specific months → 'in X and Y' branch."""
        result = describe("0 0 1 1,6 *")
        assert "January" in result
        assert "June" in result

    def test_three_or_more_months(self) -> None:
        """Three or more specific months → 'in X, Y, and Z' branch."""
        result = describe("0 0 1 1,3,6 *")
        assert "January" in result
        assert "March" in result
        assert "June" in result

    def test_three_weekdays(self) -> None:
        """Three named days of week → 'every X, Y, and Z' branch."""
        result = describe("0 0 * * 1,3,5")
        assert "Monday" in result
        assert "Wednesday" in result
        assert "Friday" in result
