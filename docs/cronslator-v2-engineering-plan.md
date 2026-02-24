# Cronslator v2 — Engineering Plan

## 1. Project Summary

Cronslator is a Python library that translates between natural language schedule descriptions and cron expressions. The current codebase (v0.2.3) was generated entirely by GitHub Copilot as an experiment. A thorough code analysis revealed critical correctness bugs, a dead class, a monolithic parsing function with no domain model, and a test suite that only covers the happy path.

This plan describes a ground-up rewrite that preserves the existing test cases as a regression baseline while introducing a layered architecture, reverse translation support, and comprehensive validation.

### What We're Keeping

- The 72 existing test cases (as a regression suite and de facto specification)
- The README example table (as the public contract)
- The `CronComponents` dataclass concept (refined)
- The lookup dictionaries (`WEEKDAYS`, `ORDINALS`, `NUMBERS`, `SPECIAL_TIMES`)
- The CLI module (with minor updates for the new package name)

### What We're Replacing

- The entire `cronslator.py` parsing implementation
- The package namespace (`pyslop.cronslator` → `cronslator`)
- The build system (Poetry → setuptools with `pyproject.toml`)
- The license (CC0 → MIT)

---

## 2. Domain Model

The core insight missing from v1 is a clean separation between *what the user means* and *how cron expresses it*. The rewrite introduces a `ScheduleIntent` as the intermediate representation that both directions of translation pass through.

```
English text ──► ScheduleIntent ──► Cron expression
                      ▲                    │
                      │                    ▼
               Cron expression ◄── ScheduleIntent ◄── English text
```

### 2.1 ScheduleIntent

This is the central domain object. It represents a parsed schedule in terms that are meaningful to humans, before any cron-specific encoding.

```python
@dataclass
class ScheduleIntent:
    """A structured representation of a schedule, independent of cron syntax."""

    # Time of day
    minutes: list[int] | None = None          # Specific minutes [0, 30]
    hours: list[int] | None = None            # Specific hours [9, 17]
    minute_interval: int | None = None        # "every N minutes"
    hour_interval: int | None = None          # "every N hours"

    # Hour range constraint (e.g., "between 9am and 5pm")
    hour_range: tuple[int, int] | None = None # (start_hour, end_hour) inclusive

    # Day of month
    days_of_month: list[int] | None = None    # Specific days [1, 15]
    day_interval: int | None = None           # "every N days"
    last_day_of_month: bool = False           # "last day of month"
    ordinal_weekday: tuple[int, str] | None = None  # (nth, "monday") → "2nd Monday"

    # Day of week
    days_of_week: list[int] | None = None     # 0=Sun, 1=Mon, ..., 6=Sat
    weekday_only: bool = False                # shorthand for [1,2,3,4,5]
    weekend_only: bool = False                # shorthand for [0,6]

    # Month
    months: list[int] | None = None           # Specific months [1, 4, 7, 10]
```

This design makes several things explicit that were implicit (and buggy) in v1:

- **Intervals vs. specific values** — `minute_interval=15` is different from `minutes=[15]`. In v1, these were conflated in the string `"*/15"` vs `"15"` with no structured distinction.
- **Range constraints** — `hour_range` is separate from `hours`, so "every 30 minutes between 9am and 5pm" is modeled as `minute_interval=30, hour_range=(9, 17)` rather than being assembled inline.
- **Ordinal weekdays** — `ordinal_weekday=(2, "monday")` explicitly captures "2nd Monday" as a concept, and the cron compiler can decide how to approximate it.

### 2.2 CronExpression

Replaces the old `CronComponents`. Adds validation and field-count configurability.

```python
@dataclass
class CronExpression:
    """A validated cron expression."""

    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"

    def validate(self) -> None:
        """Raise ValueError if any field is out of valid cron range."""
        ...

    def __str__(self) -> str:
        return f"{self.minute} {self.hour} {self.day_of_month} {self.month} {self.day_of_week}"
```

### 2.3 Domain Validation Rules

These rules live in the domain layer, not scattered through regex branches:

| Rule | Example | Behavior |
|---|---|---|
| Minute interval must be 1–59 | `"every 90 minutes"` | `ValueError: Minute interval 90 exceeds maximum of 59` |
| Hour interval must be 1–23 | `"every 25 hours"` | `ValueError: Hour interval 25 exceeds maximum of 23` |
| Hours must be 0–23 | `"at 13pm"` → hour 25 | `ValueError: Hour 25 is out of range (0-23)` |
| Days must be 1–31 | `"on day 32"` | `ValueError: Day 32 is out of range (1-31)` |
| Biweekly/bimonthly are inexpressible | `"biweekly on Monday"` | `ValueError: Biweekly schedules cannot be expressed in standard cron` |
| Combined day-of-month + day-of-week | `"first Monday"` | Works, but docstring documents the OR semantics caveat |

---

## 3. Architecture

### 3.1 Package Structure

```
cronslator/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── cronslator/
│       ├── __init__.py              # Public API: cronslate, describe, CronExpression
│       ├── model.py                 # ScheduleIntent, CronExpression dataclasses
│       ├── parsing/
│       │   ├── __init__.py
│       │   ├── tokenizer.py         # Normalize + tokenize input text
│       │   ├── patterns.py          # Pattern registry (each pattern → ScheduleIntent)
│       │   └── constants.py         # WEEKDAYS, ORDINALS, NUMBERS, SPECIAL_TIMES
│       ├── compiler.py              # ScheduleIntent → CronExpression
│       ├── describer.py             # CronExpression → English string
│       ├── validator.py             # ScheduleIntent + CronExpression validation
│       └── cli.py                   # CLI entry point
└── tests/
    ├── test_tokenizer.py
    ├── test_patterns.py
    ├── test_compiler.py
    ├── test_describer.py
    ├── test_validator.py
    ├── test_cronslate.py            # Integration: end-to-end English → cron
    ├── test_roundtrip.py            # English → cron → English consistency
    └── test_legacy_regression.py    # All 72 original test cases, unchanged
```

### 3.2 Layer Responsibilities

**Tokenizer** (`parsing/tokenizer.py`)
Normalizes input before pattern matching: lowercasing, collapsing whitespace, rejecting multi-line input, expanding contractions, replacing word-numbers with digits. The goal is to give pattern matchers a clean, consistent input.

```python
def tokenize(text: str) -> list[str]:
    """Normalize and tokenize a natural language schedule description.

    Raises ValueError for empty, whitespace-only, or multi-line input.
    """
```

**Pattern Registry** (`parsing/patterns.py`)
Each pattern is a self-contained function that either returns a `ScheduleIntent` or `None` (no match). Patterns are registered with an explicit priority number. The registry tries them in order and returns the first match.

```python
@dataclass
class Pattern:
    name: str
    priority: int              # Lower number = higher priority
    match: Callable[[list[str], str], ScheduleIntent | None]

class PatternRegistry:
    def __init__(self):
        self._patterns: list[Pattern] = []

    def register(self, name: str, priority: int):
        """Decorator to register a pattern function."""
        ...

    def parse(self, tokens: list[str], raw: str) -> ScheduleIntent:
        """Try all patterns in priority order. Raise ValueError if none match."""
        ...
```

This solves v1's biggest architectural problem: patterns are isolated, testable individually, and have explicit ordering. Adding a new pattern is a single function with a `@registry.register("pattern_name", priority=50)` decorator.

**Compiler** (`compiler.py`)
Pure function: `ScheduleIntent` → `CronExpression`. No regex, no string parsing. This is where the cron-specific logic lives (e.g., converting `ordinal_weekday=(1, "monday")` into `day_of_month="1-7", day_of_week="1"`).

```python
def compile(intent: ScheduleIntent) -> CronExpression:
    """Convert a ScheduleIntent into a validated CronExpression.

    Raises ValueError if the intent cannot be expressed in cron.
    """
```

**Describer** (`describer.py`)
The reverse path: `CronExpression` → English. Parses the cron fields back into a `ScheduleIntent` (or works directly from cron fields), then generates a human-readable description.

```python
def describe(expression: str) -> str:
    """Convert a cron expression string to a human-readable English description.

    Example: "0 3 * * 1" → "Every Monday at 3:00 AM"
    """
```

**Validator** (`validator.py`)
Validates both `ScheduleIntent` and `CronExpression`, keeping all range-checking and constraint logic in one place.

```python
def validate_intent(intent: ScheduleIntent) -> None:
    """Raise ValueError if the intent contains invalid or contradictory values."""

def validate_expression(expr: CronExpression) -> None:
    """Raise ValueError if any cron field is out of range."""
```

### 3.3 Data Flow

**English → Cron (`cronslate`)**
```
input text
  → tokenizer.tokenize()           → normalized tokens
  → pattern_registry.parse()       → ScheduleIntent
  → validator.validate_intent()    → (raises or passes)
  → compiler.compile()             → CronExpression
  → validator.validate_expression() → (raises or passes)
  → str(CronExpression)            → "0 3 * * 1"
```

**Cron → English (`describe`)**
```
cron string
  → parse cron fields              → CronExpression
  → validator.validate_expression() → (raises or passes)
  → describer.describe()           → "Every Monday at 3:00 AM"
```

---

## 4. Pattern Catalog

The patterns below are organized by priority group. Within each group, more specific patterns are tried before more general ones.

### Priority 1xx — Interval Patterns (Highest)

| Priority | Pattern Name | Example Input | ScheduleIntent |
|---|---|---|---|
| 100 | `minute_interval` | `"every 15 minutes"` | `minute_interval=15` |
| 101 | `minute_interval_ranged` | `"every 30 minutes between 9am and 5pm"` | `minute_interval=30, hour_range=(9,17)` |
| 110 | `hour_interval` | `"every 2 hours"` | `hour_interval=2` |
| 120 | `business_hours_interval` | `"every 5 minutes during business hours"` | `minute_interval=5, hour_range=(9,17), weekday_only=True` |

### Priority 2xx — Special Shorthand

| Priority | Pattern Name | Example Input | ScheduleIntent |
|---|---|---|---|
| 200 | `shorthand_hourly` | `"hourly"`, `"every hour"` | `minutes=[0]` |
| 201 | `shorthand_daily` | `"daily"`, `"every day"` | `minutes=[0], hours=[0]` |
| 202 | `shorthand_weekly` | `"weekly on Monday"` | `minutes=[0], hours=[0], days_of_week=[1]` |
| 210 | `half_hour` | `"every hour on the half hour"` | `minutes=[30]` |
| 211 | `quarter_hour` | `"every quarter hour"` | `minute_interval=15` |
| 212 | `quarter_past` | `"at quarter past each hour"` | `minutes=[15]` |

### Priority 3xx — Specific Time Patterns

| Priority | Pattern Name | Example Input | ScheduleIntent |
|---|---|---|---|
| 300 | `specific_times` | `"at 9am, 1pm and 5pm"` | `minutes=[0], hours=[9,13,17]` |
| 301 | `specific_time_with_minutes` | `"at 4:30 PM"` | `minutes=[30], hours=[16]` |
| 310 | `times_per_hour` | `"three times per hour at 15, 30, and 45"` | `minutes=[15,30,45]` |
| 320 | `first_n_minutes` | `"in the first 15 minutes of each hour"` | (special: minute field `"0-14"`) |

### Priority 4xx — Day-of-Week Patterns

| Priority | Pattern Name | Example Input | ScheduleIntent |
|---|---|---|---|
| 400 | `weekday_constraint` | `"on weekdays"` | `weekday_only=True` |
| 401 | `weekend_constraint` | `"on weekends"` | `weekend_only=True` |
| 410 | `named_days` | `"on Mondays and Fridays"` | `days_of_week=[1,5]` |

### Priority 5xx — Day-of-Month Patterns

| Priority | Pattern Name | Example Input | ScheduleIntent |
|---|---|---|---|
| 500 | `ordinal_weekday` | `"first Monday of every month"` | `ordinal_weekday=(1, "monday")` |
| 510 | `specific_day_of_month` | `"on the 15th"` | `days_of_month=[15]` |
| 511 | `day_interval` | `"every 4th day"` | `day_interval=4` |
| 520 | `last_day` | `"last day of month"` | `last_day_of_month=True` |
| 530 | `first_day` | `"first day of every month"` | `days_of_month=[1]` |
| 540 | `day_exception` | `"workdays except the 13th"` | `days_of_month=[1-12,14-31], weekday_only=True` |

### Priority 6xx — Month Patterns

| Priority | Pattern Name | Example Input | ScheduleIntent |
|---|---|---|---|
| 600 | `quarter_months` | `"each quarter"` | `months=[1,4,7,10]` |
| 610 | `named_months` | `"in January"`, `"every March"` | `months=[1]`, `months=[3]` |

### Pattern Composition

Most real inputs combine patterns across priority groups. The registry handles this by allowing a pattern to claim *part* of the intent and passing a partially-built `ScheduleIntent` through successive layers, or by having composite patterns that handle the full phrase.

The decision on whether to use single-pass "composite" patterns vs. multi-pass "additive" patterns is a key implementation detail. The recommended approach is:

- **Composite patterns** for the interval group (100-series), since they tend to be self-contained phrases.
- **Additive enrichment** for time, day-of-week, and month, which layer independently onto an existing intent (e.g., "at 3am" + "on weekdays" + "in January").

This means the registry's `parse()` method would:
1. Try all composite patterns (100s, 200s). If one matches, start with its intent.
2. Apply time enrichment (300s) to set hours/minutes if not already set.
3. Apply day-of-week enrichment (400s).
4. Apply day-of-month enrichment (500s).
5. Apply month enrichment (600s).
6. If the intent is still completely empty after all passes, raise `ValueError`.

---

## 5. Reverse Translation Design

The `describe()` function converts a cron expression back to English. This is not a simple lookup — it requires recognizing patterns in the cron fields and choosing the most natural phrasing.

### 5.1 Description Strategy

The describer works from the cron fields and reconstructs the most natural English phrasing by categorizing what it sees.

```python
# Detection priority (check in this order):
#
# 1. Interval patterns:  */N in minute or hour field
# 2. Range patterns:     N-M in hour field (constrained window)
# 3. List patterns:      N,M,O in any field (multiple values)
# 4. Specific values:    single number in a field
# 5. Wildcards:          * means "every"
```

### 5.2 Phrasing Rules

| Cron Pattern | English Output |
|---|---|
| `*/15 * * * *` | `"Every 15 minutes"` |
| `*/30 9-17 * * 1-5` | `"Every 30 minutes between 9:00 AM and 5:00 PM on weekdays"` |
| `0 3 * * 1` | `"Every Monday at 3:00 AM"` |
| `0 0 1 * *` | `"First day of every month at midnight"` |
| `0 9,13,17 * * 1-5` | `"Every weekday at 9:00 AM, 1:00 PM, and 5:00 PM"` |
| `0 */2 * * *` | `"Every 2 hours"` |
| `59 23 L * *` | `"Last day of every month at 11:59 PM"` |

### 5.3 Roundtrip Consistency

A key quality signal: `describe(cronslate(text))` should produce a semantically equivalent (though not necessarily identical) description. The test suite will include roundtrip tests for all README examples.

---

## 6. Configurability: Extended Cron Formats

5-field standard cron is the v1.0 requirement. Support for 6-field (with seconds) and 7-field (with seconds and year) is a nice-to-have that the architecture should accommodate without requiring a rewrite.

### 6.1 How the Architecture Supports This

The `CronExpression` dataclass gains optional fields:

```python
@dataclass
class CronExpression:
    second: str | None = None       # Optional 6th field
    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"
    year: str | None = None         # Optional 7th field

    def __init__(self, ..., format: CronFormat = CronFormat.STANDARD):
        ...
```

The `ScheduleIntent` model already has room for seconds (`second_interval`, `seconds` fields could be added). The compiler would check the target format and raise if the intent requires fields the format doesn't support.

### 6.2 Scoping

This is explicitly **out of scope for v1.0**. The plan documents it here so that v1.0 implementation choices don't accidentally prevent it. Specifically:

- Don't hardcode "5 fields" in the validator — make it configurable.
- Don't assume field positions in the describer — use named access.
- Keep the `CronExpression.__str__()` method aware of optional fields.

---

## 7. Error Handling Philosophy

All errors are `ValueError` with clear, actionable messages. The goal is that a user can read the error and understand exactly what went wrong and what they should do instead.

### 7.1 Error Categories

| Category | Example Message |
|---|---|
| Empty/invalid input | `"Schedule description cannot be empty"` |
| Unparseable input | `"Could not understand schedule: 'wobble the timeline'. Try phrases like 'every Monday at 3am' or 'every 15 minutes'."` |
| Out of range | `"Minute interval 90 is out of range (1-59)"` |
| Inexpressible in cron | `"Biweekly schedules cannot be expressed in standard 5-field cron"` |
| Ambiguous input | `"Ambiguous schedule: 'every other day' could mean every 2 days or alternating days. Try 'every 2 days' instead."` |
| Invalid cron (describe) | `"Invalid cron expression: hour field '25' is out of range (0-23)"` |

### 7.2 No Silent Failures

The v1 codebase's worst behavior was producing *valid-looking but incorrect* cron expressions. The v2 rule is: if we can't confidently produce the right answer, raise. It is always better to tell the user "I don't understand" than to silently schedule their job at the wrong time.

---

## 8. Test Strategy

### 8.1 Test Layers

| Layer | File | What It Tests | Approach |
|---|---|---|---|
| Tokenizer | `test_tokenizer.py` | Normalization, whitespace, rejection | Unit tests |
| Patterns | `test_patterns.py` | Each pattern function in isolation | Unit tests with `ScheduleIntent` assertions |
| Compiler | `test_compiler.py` | `ScheduleIntent` → `CronExpression` | Unit tests, no string parsing involved |
| Describer | `test_describer.py` | `CronExpression` → English | Unit tests for each phrasing rule |
| Validator | `test_validator.py` | Range checks, constraint violations | Unit tests for every error case |
| Integration | `test_cronslate.py` | Full English → cron pipeline | Parametrized, covers README examples |
| Roundtrip | `test_roundtrip.py` | `describe(cronslate(x))` semantic equivalence | Parametrized |
| Regression | `test_legacy_regression.py` | All 72 original test cases verbatim | Direct port from v1 |
| Property | `test_properties.py` | Fuzz with Hypothesis | See below |

### 8.2 Property-Based Tests (Hypothesis)

These tests don't check specific outputs — they check *invariants* that must always hold:

```python
# Property 1: Output is always valid cron
@given(st.text(min_size=1, max_size=200))
def test_output_is_valid_or_raises(text):
    """cronslate either returns valid cron or raises ValueError. Never invalid cron."""
    try:
        result = cronslate(text)
        validate_cron_expression(result)  # Must not raise
    except ValueError:
        pass  # Expected for unparseable input

# Property 2: Roundtrip doesn't crash
@given(valid_cron_expressions())
def test_describe_doesnt_crash(expr):
    """describe() either returns a string or raises ValueError for invalid input."""
    result = describe(expr)
    assert isinstance(result, str)
    assert len(result) > 0

# Property 3: All cron field values are in range
@given(st.text(min_size=1, max_size=200))
def test_fields_in_range(text):
    """Every field in cronslate() output is within valid cron ranges."""
    try:
        result = cronslate(text)
        fields = result.split()
        assert len(fields) == 5
        # Each field: validate against known cron grammar
    except ValueError:
        pass
```

### 8.3 Coverage Target

The goal is 95%+ line coverage on `model.py`, `compiler.py`, `validator.py`, and `describer.py`. The `patterns.py` module will have lower coverage since some patterns are hit by integration tests rather than unit tests, but each pattern function should have at least one dedicated unit test.

---

## 9. Implementation Phases

### Phase 1: Foundation (Estimated: 2–3 sessions)

**Goal:** Core domain model and infrastructure, passing the 72 legacy tests.

Tasks:
- [ ] Initialize new project structure with `pyproject.toml` (setuptools)
- [ ] Implement `ScheduleIntent` and `CronExpression` dataclasses in `model.py`
- [ ] Implement `validator.py` with all range checks
- [ ] Implement `compiler.py` (ScheduleIntent → CronExpression)
- [ ] Implement `tokenizer.py`
- [ ] Implement pattern registry framework in `patterns.py`
- [ ] Port the 72 legacy test cases to `test_legacy_regression.py`
- [ ] Implement patterns until all 72 legacy tests pass
- [ ] Write unit tests for tokenizer, compiler, and validator

**Exit criteria:** All 72 legacy tests pass. Compiler and validator have dedicated unit tests. `cronslate("every 90 minutes")` raises `ValueError`.

### Phase 2: Reverse Translation (Estimated: 1–2 sessions)

**Goal:** `describe()` works for all standard cron patterns.

Tasks:
- [ ] Implement `describer.py` with phrasing rules
- [ ] Write `test_describer.py` with unit tests for each phrasing pattern
- [ ] Write `test_roundtrip.py` covering all README examples
- [ ] Add `describe` to public API in `__init__.py`
- [ ] Update CLI to support `cronslate --describe "*/15 * * * *"`

**Exit criteria:** `describe()` produces readable English for every cron pattern in the README table. Roundtrip tests pass.

### Phase 3: Expanded Coverage (Estimated: 1–2 sessions)

**Goal:** Handle common phrases that v1 missed, harden edge cases.

Tasks:
- [ ] Add patterns for: `"hourly"`, `"daily"`, `"weekly"`, `"every hour"`, `"every N hours"`, month names
- [ ] Add explicit `ValueError` for inexpressible concepts: `"biweekly"`, `"every 90 minutes"`, `"every last Friday"`
- [ ] Add Hypothesis property tests
- [ ] Add edge case tests: whitespace, very long input, multi-line, unicode, negative numbers
- [ ] Review and document the day-of-month + day-of-week OR semantics caveat

**Exit criteria:** All common shorthand phrases work. Property tests find no new bugs. Edge cases either produce correct output or raise clear errors.

### Phase 4: Polish & Release (Estimated: 1 session)

**Goal:** Package ready for PyPI publication.

Tasks:
- [ ] Write updated README with new examples, `describe()` usage, and error handling guidance
- [ ] Add `py.typed` marker and verify type checking with mypy
- [ ] Add `__version__` attribute
- [ ] Set up GitHub Actions for CI (pytest, mypy, coverage report)
- [ ] Publish to TestPyPI, verify installation
- [ ] Publish to PyPI as `cronslator`

**Exit criteria:** `pip install cronslator` works. CI is green. README is accurate. Coverage ≥ 95% on core modules.

### Future: Extended Cron Formats (Unscheduled)

- Add `CronFormat` enum (`STANDARD`, `WITH_SECONDS`, `QUARTZ`)
- Extend `ScheduleIntent` with seconds fields
- Extend compiler and describer for 6/7-field formats
- Add `format` parameter to `cronslate()` and `describe()`

---

## 10. Public API Surface

The library exposes a deliberately minimal public API:

```python
import cronslator

# English → Cron
cron = cronslator.cronslate("Every Monday at 3am")
# "0 3 * * 1"

# Cron → English
text = cronslator.describe("0 3 * * 1")
# "Every Monday at 3:00 AM"

# Direct access to domain objects (for advanced use)
from cronslator.model import ScheduleIntent, CronExpression
```

CLI:
```bash
# English → Cron
cronslate "Every Monday at 3am"
# 0 3 * * 1

# Cron → English
cronslate --describe "0 3 * * 1"
# Every Monday at 3:00 AM

# Piped input
echo "Every 15 minutes" | cronslate
# */15 * * * *
```

---

## 11. Dependencies

### Runtime
None. The library uses only the Python standard library (`re`, `dataclasses`).

### Development
- `pytest` — test runner
- `hypothesis` — property-based testing
- `mypy` — type checking
- `coverage` — coverage reporting

```toml
[project]
name = "cronslator"
version = "1.0.0"
requires-python = ">=3.10"
license = "MIT"

[project.scripts]
cronslate = "cronslator.cli:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project.optional-dependencies]
dev = ["pytest>=8.0", "hypothesis>=6.0", "mypy>=1.0", "coverage>=7.0"]
```

Note: Python minimum raised from 3.9 to 3.10 to use `X | Y` union syntax and `match` statements natively.

---

## 12. Open Questions

These are decisions that can be deferred to implementation time but should be consciously resolved:

1. **Pattern composition strategy** — Should composite patterns handle full phrases, or should the registry do multi-pass additive enrichment? Section 4 recommends a hybrid, but this needs validation during Phase 1. Answer: Hybrid as recommended

2. **Ambiguity handling** — Should `"every day"` mean `0 0 * * *` (once at midnight) or `"every day at what time?"` (raise asking for a time)? Current recommendation: default to midnight, matching user expectations for shorthand.  Answer: Default to midnight

3. **Ordinal weekday OR-semantics warning** — Should `cronslate()` emit a warning (via `warnings.warn`) when producing a cron expression that relies on day-of-month + day-of-week AND-semantics that most cron daemons interpret as OR? Or just document it? Answer: Emit a warning

4. **`describe()` phrasing preferences** — Should it say `"12:00 AM"` or `"midnight"`? `"Monday through Friday"` or `"weekdays"`? Current recommendation: prefer the more natural/shorter phrasing, with a `verbose=True` option if needed later. Answer: Follow the recommendation
