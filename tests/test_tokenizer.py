"""Unit tests for the tokenizer module."""

import pytest

from recronslator.parsing.tokenizer import tokenize


class TestBasicNormalization:
    def test_lowercases_input(self) -> None:
        assert tokenize("EVERY MONDAY") == "every monday"

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert tokenize("  every monday  ") == "every monday"

    def test_collapses_internal_whitespace(self) -> None:
        assert tokenize("every   monday  at   3am") == "every monday at 3am"


class TestRejection:
    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            tokenize("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            tokenize("   ")

    def test_multiline_raises(self) -> None:
        with pytest.raises(ValueError, match="single line"):
            tokenize("every monday\nat noon")

    def test_multiline_carriage_return_raises(self) -> None:
        with pytest.raises(ValueError, match="single line"):
            tokenize("every monday\rat noon")


class TestInexpressiblePatterns:
    def test_biweekly_raises(self) -> None:
        with pytest.raises(ValueError, match="Biweekly"):
            tokenize("biweekly on monday")

    def test_every_other_week_raises(self) -> None:
        with pytest.raises(ValueError, match="Biweekly"):
            tokenize("every other week on friday")

    def test_bimonthly_raises(self) -> None:
        with pytest.raises(ValueError, match="Bimonthly"):
            tokenize("bimonthly on the 1st")


class TestWordNumberExpansion:
    def test_fifteen_expands(self) -> None:
        assert "15" in tokenize("every fifteen minutes")

    def test_thirty_expands(self) -> None:
        assert "30" in tokenize("every thirty minutes")

    def test_four_expands(self) -> None:
        assert "4" in tokenize("every four days")

    def test_mixed_case_expands(self) -> None:
        assert "15" in tokenize("EVERY FIFTEEN minutes")

    def test_ordinal_digit_preserved(self) -> None:
        # "3rd" should remain as-is
        result = tokenize("3rd day of every month")
        assert "3rd" in result

    # ------------------------------------------------------------------
    # Compound word-numbers (previously unsupported)
    # ------------------------------------------------------------------

    def test_twenty_five_hyphen(self) -> None:
        assert tokenize("every twenty-five minutes") == "every 25 minutes"

    def test_thirty_one_hyphen(self) -> None:
        assert tokenize("every thirty-one days") == "every 31 days"

    def test_forty_two_hyphen(self) -> None:
        assert tokenize("every forty-two minutes") == "every 42 minutes"

    def test_twenty_one_space(self) -> None:
        """Space-separated compound is also accepted."""
        assert tokenize("every twenty one days") == "every 21 days"

    def test_fifty_nine_hyphen(self) -> None:
        assert tokenize("at fifty-nine minutes past") == "at 59 minutes past"

    def test_tens_alone_unchanged(self) -> None:
        """Tens word without a ones suffix still expands correctly."""
        assert tokenize("every twenty minutes") == "every 20 minutes"

    def test_compound_does_not_consume_non_digit_word(self) -> None:
        """A word that follows a tens word but is not a ones digit is left alone."""
        result = tokenize("every twenty minutes on friday")
        assert "20" in result
        assert "minutes" in result
