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
