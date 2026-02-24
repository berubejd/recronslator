"""recronslator — natural language ↔ cron expression translator.

A ground-up rewrite of pyslop/cronslator (https://github.com/pyslop/cronslator)
with a clean domain model, reverse translation, and strict validation.

Public API::

    import recronslator

    # English → Cron
    cron = recronslator.cronslate("Every Monday at 3am")
    # "0 3 * * 1"

    # Cron → English
    text = recronslator.describe("0 3 * * 1")
    # "Every Monday at 3:00 AM"

    # Direct dataclass access (advanced use)
    from recronslator.model import ScheduleIntent, CronExpression
"""

from __future__ import annotations

from recronslator.compiler import compile_intent
from recronslator.describer import describe as _describe_impl
from recronslator.model import CronExpression, ScheduleIntent
from recronslator.parsing import parse, tokenize
from recronslator.validator import validate_intent

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "cronslate",
    "describe",
    "CronExpression",
    "ScheduleIntent",
]


def cronslate(text: str) -> str:
    """Translate a natural language schedule description to a cron expression.

    Pipeline: tokenize → parse → validate_intent → compile → str

    Args:
        text: A natural language schedule description, e.g. "Every Monday at 3am"

    Returns:
        A 5-field cron expression string, e.g. "0 3 * * 1"

    Raises:
        ValueError: If the input is empty, unparseable, or describes a schedule
                    that cannot be expressed in standard 5-field cron.

    Examples::

        >>> cronslate("Every Monday at 3am")
        '0 3 * * 1'
        >>> cronslate("Every 15 minutes")
        '*/15 * * * *'
        >>> cronslate("Every 30 minutes between 9am and 5pm on weekdays")
        '*/30 9-17 * * 1-5'
    """
    normalized = tokenize(text)
    intent = parse(normalized)
    validate_intent(intent)
    expr = compile_intent(intent)
    return str(expr)


def describe(expression: str) -> str:
    """Translate a 5-field cron expression to a human-readable English description.

    Args:
        expression: A 5-field cron expression string, e.g. "0 3 * * 1"

    Returns:
        A natural language description, e.g. "Every Monday at 3:00 AM"

    Raises:
        ValueError: If the expression is invalid or has the wrong number of fields.

    Examples::

        >>> describe("0 3 * * 1")
        'Every Monday at 3:00 AM'
        >>> describe("*/15 * * * *")
        'Every 15 minutes'
    """
    return _describe_impl(expression)
