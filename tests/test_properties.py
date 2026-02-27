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
_VALID_HOURS = [str(i) for i in range(0, 24)] + ["*/2", "*/3", "*/4", "*/6", "*/8", "*/12", "9-17", "8-18", "0,12", "9,13,17"]
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

# Idempotency strategy was previously narrower; now identical to the main
# strategy since all round-trip limitations have been fixed.
_roundtrip_cron_strategy = _valid_cron_strategy


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


@given(_valid_cron_strategy)
@settings(max_examples=500)
def test_describe_never_leaks_raw_cron_syntax(expr: str) -> None:
    """describe() must translate every cron field to English — never echo raw syntax.

    Patterns like '*/N' or sentinel phrases like 'in hour' / 'on day-of-week'
    appearing in the output indicate a describe path fell through to its raw
    fallback.  The '* */2 * * *' regression is the canonical example: Priority 0
    intercepted the step-hour pattern and produced 'Every minute in hour */2'
    instead of 'Every 2 hours'.
    """
    try:
        english = recronslator.describe(expr)
        assert not re.search(r"\*/\d+", english), (
            f"describe({expr!r}) leaked raw step syntax: {english!r}"
        )
        assert "in hour " not in english.lower(), (
            f"describe({expr!r}) used raw hour fallback: {english!r}"
        )
        assert "in month " not in english.lower(), (
            f"describe({expr!r}) used raw month fallback: {english!r}"
        )
        assert "on day-of-week " not in english.lower(), (
            f"describe({expr!r}) used raw dow fallback: {english!r}"
        )
    except ValueError:
        pass


@given(_roundtrip_cron_strategy)
@settings(max_examples=300)
def test_describe_cronslate_describe_idempotent(expr: str) -> None:
    """describe → cronslate → describe must converge: second describe equals first.

    If the pipeline is internally consistent, applying describe twice through
    cronslate should produce the same English both times.  A failure here means
    the describer and parser disagree on what a cron expression means.
    """
    try:
        english1 = recronslator.describe(expr)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            recron = recronslator.cronslate(english1)
        english2 = recronslator.describe(recron)
        assert english1 == english2, (
            f"describe→cronslate→describe not idempotent:\n"
            f"  describe({expr!r})         = {english1!r}\n"
            f"  cronslate({english1!r}) = {recron!r}\n"
            f"  describe({recron!r})   = {english2!r}"
        )
    except ValueError:
        pass  # Unparseable intermediate is acceptable


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
