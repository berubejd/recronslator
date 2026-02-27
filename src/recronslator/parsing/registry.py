"""Pattern registry infrastructure.

The registry holds all composite patterns and additive enrichers.  Pattern
modules register themselves at import time via the ``@registry.register``
decorator.  The ``parse()`` method runs composites first (first-match-wins),
then layers enrichers onto the result.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Callable

from recronslator.model import ScheduleIntent


@dataclass
class Pattern:
    name: str
    priority: int
    match: Callable[[str], ScheduleIntent | None]
    is_composite: bool = True  # False = additive enricher


class PatternRegistry:
    def __init__(self) -> None:
        self._patterns: list[Pattern] = []

    def register(
        self,
        name: str,
        priority: int,
        *,
        composite: bool = True,
    ) -> Callable[[Callable[[str], ScheduleIntent | None]], Callable[[str], ScheduleIntent | None]]:
        """Decorator to register a pattern function."""
        def decorator(
            fn: Callable[[str], ScheduleIntent | None]
        ) -> Callable[[str], ScheduleIntent | None]:
            self._patterns.append(
                Pattern(name=name, priority=priority, match=fn, is_composite=composite)
            )
            self._patterns.sort(key=lambda p: p.priority)
            return fn
        return decorator

    def parse(self, text: str) -> ScheduleIntent:
        """Try all patterns and return a populated ScheduleIntent.

        Step 1: Try composite patterns in priority order. The first match
                wins and provides the base intent.
        Step 2: Run additive enrichers in priority order, mutating the intent
                in place.
        Step 3: If the intent has no meaningful content, raise ValueError.
        """
        composites = [p for p in self._patterns if p.is_composite]
        enrichers = [p for p in self._patterns if not p.is_composite]

        intent: ScheduleIntent | None = None

        for pattern in composites:
            result = pattern.match(text)
            if result is not None:
                intent = result
                break

        if intent is None:
            intent = ScheduleIntent()

        for enricher in enrichers:
            result = enricher.match(text)
            if result is not None:
                _merge_intent(intent, result)

        return intent


def _merge_intent(base: ScheduleIntent, addition: ScheduleIntent) -> None:
    """Merge non-None fields from addition into base (additive enrichment)."""
    for f in fields(addition):
        val = getattr(addition, f.name)
        if val is None or val is False:
            continue
        existing = getattr(base, f.name)
        if existing is None or existing is False:
            setattr(base, f.name, val)


# Singleton instance — pattern modules import this and decorate onto it.
registry = PatternRegistry()
