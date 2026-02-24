"""Roundtrip tests: describe(cronslate(x)) should produce a semantically
meaningful (though not necessarily identical) English description.

These tests verify that:
1. The pipeline doesn't crash on README examples.
2. The described output is a non-empty string.
3. Key semantic tokens (day name, time, etc.) are preserved.
"""

import warnings

import pytest

import recronslator


def cronslate(text: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return recronslator.cronslate(text)


@pytest.mark.parametrize(
    "description,expected_cron",
    [
        ("Every Monday at 3am", "0 3 * * 1"),
        ("Every weekday at noon", "0 12 * * 1-5"),
        ("Every 15 minutes", "*/15 * * * *"),
        ("First day of every month at midnight", "0 0 1 * *"),
        ("Every Sunday at 4:30 PM", "30 16 * * 0"),
        ("Every hour on the half hour", "30 * * * *"),
        ("Every day at 2am and 2pm", "0 2,14 * * *"),
        ("Every 30 minutes between 9am and 5pm on weekdays", "*/30 9-17 * * 1-5"),
        ("First Monday of every month at 3am", "0 3 1-7 * 1"),
        ("Every quarter hour between 2pm and 6pm", "*/15 14-18 * * *"),
        ("Every weekend at 10pm", "0 22 * * 0,6"),
        ("Every 5 minutes during business hours", "*/5 9-17 * * 1-5"),
        ("3rd day of every month at 1:30am", "30 1 3 * *"),
        ("Every weekday at 9am, 1pm and 5pm", "0 9,13,17 * * 1-5"),
        ("At midnight on Mondays and Fridays", "0 0 * * 1,5"),
        ("Twice daily at 6:30 and 18:30", "30 6,18 * * *"),
        ("Monthly on the 15th at noon", "0 12 15 * *"),
        ("Three times per hour at 15, 30, and 45 minutes", "15,30,45 * * * *"),
        ("Last day of month at 11:59 PM", "59 23 L * *"),
        ("Weekdays at quarter past each hour", "15 * * * 1-5"),
        ("Once per hour in the first 15 minutes", "0-14 * * * *"),
        ("Workdays at 8:45 AM except on the 13th", "45 8 1-12,14-31 * 1-5"),
        ("First 5 days of each quarter at dawn", "0 6 1-5 1,4,7,10 *"),
    ],
)
def test_roundtrip_does_not_crash(description: str, expected_cron: str) -> None:
    """cronslate followed by describe should not raise."""
    cron = cronslate(description)
    assert cron == expected_cron  # cron output is correct
    english = recronslator.describe(cron)
    assert isinstance(english, str)
    assert len(english) > 0


@pytest.mark.parametrize(
    "cron,keywords",
    [
        ("0 3 * * 1", ["Monday", "3:00 AM"]),
        ("0 12 * * 1-5", ["weekday"]),
        ("*/15 * * * *", ["15"]),
        ("0 0 1 * *", ["1"]),
        ("30 16 * * 0", ["Sunday", "4:30 PM"]),
        ("*/30 9-17 * * 1-5", ["30", "9:00 AM", "5:00 PM"]),
        ("0 22 * * 0,6", ["weekend"]),
        ("59 23 L * *", ["last"]),
    ],
)
def test_describe_contains_key_tokens(cron: str, keywords: list[str]) -> None:
    """Key semantic tokens from the cron expression appear in the description."""
    result = recronslator.describe(cron)
    result_lower = result.lower()
    for kw in keywords:
        assert kw.lower() in result_lower, (
            f"Expected {kw!r} in describe({cron!r}), got {result!r}"
        )


def test_cron_to_english_to_cron_is_stable() -> None:
    """describe → cronslate → compare with original (semantic equivalence check).

    For a subset of simple patterns, the re-translated cron should match.
    """
    stable_pairs = [
        ("*/15 * * * *", "*/15 * * * *"),
        ("0 3 * * 1", "0 3 * * 1"),
        ("0 12 * * 1-5", "0 12 * * 1-5"),
    ]
    for original_cron, expected_recron in stable_pairs:
        english = recronslator.describe(original_cron)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            recron = recronslator.cronslate(english)
        assert recron == expected_recron, (
            f"describe({original_cron!r}) = {english!r}\n"
            f"cronslate({english!r}) = {recron!r} (expected {expected_recron!r})"
        )
