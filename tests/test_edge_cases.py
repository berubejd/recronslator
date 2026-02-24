"""Edge case tests: whitespace, casing, boundary values, unicode, etc."""

import warnings

import pytest

import recronslator


def cronslate(text: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return recronslator.cronslate(text)


class TestWhitespace:
    def test_leading_whitespace(self) -> None:
        assert cronslate("  Every Monday at 3am") == "0 3 * * 1"

    def test_trailing_whitespace(self) -> None:
        assert cronslate("Every Monday at 3am  ") == "0 3 * * 1"

    def test_internal_extra_spaces(self) -> None:
        assert cronslate("Every   Monday  at  3am") == "0 3 * * 1"

    def test_tab_character(self) -> None:
        assert cronslate("Every\tMonday\tat\t3am") == "0 3 * * 1"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            cronslate("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            cronslate("   ")

    def test_multiline_raises(self) -> None:
        with pytest.raises(ValueError, match="single line"):
            cronslate("every monday\nat 3am")


class TestCaseInsensitivity:
    def test_all_upper(self) -> None:
        assert cronslate("EVERY 15 MINUTES") == "*/15 * * * *"

    def test_all_lower(self) -> None:
        assert cronslate("every 15 minutes") == "*/15 * * * *"

    def test_title_case(self) -> None:
        assert cronslate("Every 15 Minutes") == "*/15 * * * *"

    def test_mixed_case_day(self) -> None:
        assert cronslate("every MONDAY at 3AM") == "0 3 * * 1"


class TestBoundaryValues:
    def test_minute_0(self) -> None:
        assert cronslate("every monday at midnight") == "0 0 * * 1"

    def test_minute_59(self) -> None:
        assert cronslate("last day of month at 11:59 pm") == "59 23 L * *"

    def test_hour_0(self) -> None:
        assert cronslate("every day at midnight") == "0 0 * * *"

    def test_hour_23(self) -> None:
        assert cronslate("every 4 days at 11 pm") == "0 23 */4 * *"

    def test_dom_1(self) -> None:
        result = cronslate("first day of every month at midnight")
        assert result.split()[2] == "1"

    def test_dom_31_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            cronslate("on the 32nd of the month at noon")

    def test_invalid_minute_interval_90(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            cronslate("every 90 minutes")

    def test_invalid_hour_25(self) -> None:
        with pytest.raises(ValueError):
            cronslate("at 25:00")


class TestInexpressibleSchedules:
    def test_biweekly(self) -> None:
        with pytest.raises(ValueError, match="[Bb]iweekly"):
            cronslate("biweekly on monday")

    def test_bimonthly(self) -> None:
        with pytest.raises(ValueError, match="[Bb]imonthly"):
            cronslate("bimonthly on the 15th")

    def test_every_other_week(self) -> None:
        with pytest.raises(ValueError):
            cronslate("every other week on thursday")


class TestNonsenseInputs:
    def test_random_words_raises(self) -> None:
        with pytest.raises(ValueError):
            cronslate("wobble the timeline")

    def test_single_word_raises(self) -> None:
        with pytest.raises(ValueError):
            cronslate("nananosecond")

    def test_numbers_only_raises(self) -> None:
        with pytest.raises(ValueError):
            cronslate("12345")

    def test_punctuation_only_raises(self) -> None:
        with pytest.raises(ValueError):
            cronslate("!@#$%")


class TestDescribeEdgeCases:
    def test_wildcard_expression(self) -> None:
        result = recronslator.describe("* * * * *")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_wrong_field_count_raises(self) -> None:
        with pytest.raises(ValueError, match="5-field"):
            recronslator.describe("0 * * *")

    def test_too_many_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="5-field"):
            recronslator.describe("0 0 1 1 0 2026")

    def test_describe_invalid_minute_raises(self) -> None:
        with pytest.raises(ValueError):
            recronslator.describe("60 * * * *")

    def test_describe_invalid_hour_raises(self) -> None:
        with pytest.raises(ValueError):
            recronslator.describe("0 24 * * *")


class TestWarningBehavior:
    def test_ordinal_weekday_does_not_warn(self) -> None:
        """Ordinal weekday pattern intentionally sets both dom and dow — no warning."""
        import warnings as _warnings
        with _warnings.catch_warnings(record=True) as w:
            _warnings.simplefilter("always")
            recronslator.cronslate("first monday of every month at 3am")
        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_explicit_dom_and_dow_warns(self) -> None:
        """Combining explicit day-of-month and day-of-week triggers an OR-semantics warning."""
        import warnings as _warnings
        with _warnings.catch_warnings(record=True) as w:
            _warnings.simplefilter("always")
            from recronslator.compiler import compile_intent
            from recronslator.model import ScheduleIntent
            compile_intent(ScheduleIntent(
                days_of_month=[15],
                days_of_week=[1],
                minutes=[0], hours=[0]
            ))
        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 1
        assert "OR" in str(user_warnings[0].message)
