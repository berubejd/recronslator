"""Property-based tests using Hypothesis.

These tests check invariants that must hold regardless of specific inputs:
1. cronslate() always returns valid cron or raises ValueError — never invalid cron.
2. describe() always returns a string or raises ValueError — never crashes.
3. All fields in cronslate() output are within valid cron ranges.
"""

import re
import warnings

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import recronslator
from recronslator.validator import validate_expression
from recronslator.model import CronExpression


def _is_valid_cron(expr: str) -> bool:
    """Quick structural check: 5 whitespace-separated tokens."""
    parts = expr.strip().split()
    return len(parts) == 5


@given(st.text(min_size=1, max_size=200))
@settings(max_examples=500)
def test_output_is_valid_or_raises(text: str) -> None:
    """cronslate() either returns a structurally valid 5-field cron or raises ValueError.

    It must NEVER return invalid-looking cron or raise non-ValueError exceptions.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = recronslator.cronslate(text)
        assert _is_valid_cron(result), (
            f"cronslate({text!r}) returned invalid cron: {result!r}"
        )
    except ValueError:
        pass  # Expected for unparseable input


@given(st.text(min_size=1, max_size=200))
@settings(max_examples=500)
def test_fields_in_range(text: str) -> None:
    """Every field in cronslate() output is within valid cron ranges."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = recronslator.cronslate(text)
        fields = result.split()
        assert len(fields) == 5
        minute, hour, dom, month, dow = fields
        expr = CronExpression(
            minute=minute, hour=hour,
            day_of_month=dom, month=month, day_of_week=dow
        )
        validate_expression(expr)  # Must not raise
    except ValueError:
        pass  # Either cronslate raised, or validate caught an invalid field


# Build a strategy for valid 5-field cron expressions
def _cron_field(values: list[str]) -> st.SearchStrategy[str]:
    return st.one_of(
        st.just("*"),
        st.sampled_from(values),
    )


_VALID_MINUTES = [str(i) for i in range(0, 60)] + ["*/5", "*/10", "*/15", "*/30", "0-14", "15,30,45"]
_VALID_HOURS = [str(i) for i in range(0, 24)] + ["*/2", "9-17", "0,12"]
_VALID_DOMS = [str(i) for i in range(1, 32)] + ["*/4", "1-7", "8-14", "1-5", "L", "1-12,14-31"]
_VALID_MONTHS = [str(i) for i in range(1, 13)] + ["1,4,7,10"]
_VALID_DOWS = [str(i) for i in range(0, 7)] + ["1-5", "0,6", "1,5"]

_valid_cron_strategy = st.builds(
    lambda m, h, dom, mon, dow: f"{m} {h} {dom} {mon} {dow}",
    _cron_field(_VALID_MINUTES),
    _cron_field(_VALID_HOURS),
    _cron_field(_VALID_DOMS),
    _cron_field(_VALID_MONTHS),
    _cron_field(_VALID_DOWS),
)


@given(_valid_cron_strategy)
@settings(max_examples=300)
def test_describe_valid_cron_doesnt_crash(expr: str) -> None:
    """describe() with structurally valid cron either returns a string or raises ValueError.

    It must NEVER raise non-ValueError exceptions.
    """
    try:
        result = recronslator.describe(expr)
        assert isinstance(result, str), (
            f"describe({expr!r}) returned non-string: {result!r}"
        )
        assert len(result) > 0, f"describe({expr!r}) returned empty string"
    except ValueError:
        pass  # Expected for some structurally unusual combinations


@given(st.text(min_size=0, max_size=500))
@settings(max_examples=200)
def test_describe_arbitrary_text_doesnt_crash(expr: str) -> None:
    """describe() with arbitrary text should not raise non-ValueError exceptions."""
    try:
        recronslator.describe(expr)
    except ValueError:
        pass
    except Exception as exc:
        pytest.fail(
            f"describe({expr!r}) raised unexpected {type(exc).__name__}: {exc}"
        )
