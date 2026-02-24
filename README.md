# recronslator

**Natural language ↔ cron expression translator for Python.**

`recronslator` is a ground-up rewrite of the original [pyslop/cronslator](https://github.com/pyslop/cronslator) project. It adds a clean layered architecture, reverse translation (cron → English), comprehensive validation, and a property-tested implementation with zero runtime dependencies.

## Origin

This project is inspired by and derived from [pyslop/cronslator](https://github.com/pyslop/cronslator), a Copilot-generated experiment in natural language cron translation. `recronslator` rewrites the core from scratch with:

- A structured domain model (`ScheduleIntent`, `CronExpression`) as an intermediate representation
- A pattern registry with explicit priority and additive enrichment
- Reverse translation: cron → English via `describe()`
- Strict validation that raises `ValueError` with clear messages rather than producing silently wrong cron
- Hypothesis-based property tests

## Understanding Cron Format

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

## Installation

```bash
pip install recronslator
```

## Usage

### As a Python library

```python
import recronslator

# English → Cron
cron = recronslator.cronslate("Every Monday at 3am")
print(cron)  # 0 3 * * 1

# Cron → English (reverse translation)
text = recronslator.describe("0 3 * * 1")
print(text)  # Every Monday at 3:00 AM

# More examples
recronslator.cronslate("Every 15 minutes")                        # */15 * * * *
recronslator.cronslate("Every 30 minutes between 9am and 5pm on weekdays")  # */30 9-17 * * 1-5
recronslator.cronslate("First Monday of every month at 3am")      # 0 3 1-7 * 1
recronslator.cronslate("Last day of month at 11:59 PM")           # 59 23 L * *
recronslator.cronslate("First 5 days of each quarter at dawn")    # 0 6 1-5 1,4,7,10 *
```

### As a command-line tool

```bash
# English → Cron
recronslate "Every Monday at 3am"
# 0 3 * * 1

# Cron → English
recronslate --describe "0 3 * * 1"
# Every Monday at 3:00 AM

# Pipe input
echo "Every 15 minutes" | recronslate
# */15 * * * *

# Also available as 'cronslate' (alias)
cronslate "Every weekday at noon"
# 0 12 * * 1-5
```

## Supported Patterns

| Natural Language | Cron Expression |
|---|---|
| Every Monday at 3am | `0 3 * * 1` |
| Every weekday at noon | `0 12 * * 1-5` |
| Every 15 minutes | `*/15 * * * *` |
| First day of every month at midnight | `0 0 1 * *` |
| Every Sunday at 4:30 PM | `30 16 * * 0` |
| Every hour on the half hour | `30 * * * *` |
| Every day at 2am and 2pm | `0 2,14 * * *` |
| Every 30 minutes between 9am and 5pm on weekdays | `*/30 9-17 * * 1-5` |
| First Monday of every month at 3am | `0 3 1-7 * 1` |
| Every quarter hour between 2pm and 6pm | `*/15 14-18 * * *` |
| Every weekend at 10pm | `0 22 * * 0,6` |
| Every 5 minutes during business hours | `*/5 9-17 * * 1-5` |
| 3rd day of every month at 1:30am | `30 1 3 * *` |
| Every weekday at 9am, 1pm and 5pm | `0 9,13,17 * * 1-5` |
| At midnight on Mondays and Fridays | `0 0 * * 1,5` |
| Twice daily at 6:30 and 18:30 | `30 6,18 * * *` |
| Monthly on the 15th at noon | `0 12 15 * *` |
| Three times per hour at 15, 30, and 45 minutes | `15,30,45 * * * *` |
| Last day of month at 11:59 PM | `59 23 L * *` |
| Weekdays at quarter past each hour | `15 * * * 1-5` |
| Once per hour in the first 15 minutes | `0-14 * * * *` |
| Workdays at 8:45 AM except on the 13th | `45 8 1-12,14-31 * 1-5` |
| First 5 days of each quarter at dawn | `0 6 1-5 1,4,7,10 *` |

## Error Handling

All errors are `ValueError` with clear, actionable messages:

```python
from recronslator import cronslate

# Empty input
cronslate("")
# ValueError: Schedule description cannot be empty

# Unparseable input
cronslate("wobble the timeline")
# ValueError: Could not understand schedule: 'wobble the timeline'. Try phrases like...

# Out of range
cronslate("every 90 minutes")
# ValueError: Minute interval 90 is out of range (1-59)

# Inexpressible in standard cron
cronslate("biweekly on monday")
# ValueError: Biweekly schedules cannot be expressed in standard 5-field cron

# Invalid time
cronslate("at 25:00")
# ValueError: Hour 25 is out of range (0-23)
```

## Day-of-Month + Day-of-Week Warning

When a cron expression sets both `day-of-month` and `day-of-week`, most cron
daemons (including vixie cron) treat this as **OR** rather than AND. For example,
`0 3 15 * 1` runs at 3am on the 15th of the month *and* every Monday — not only
on Mondays that fall on the 15th.

`recronslator` emits a `UserWarning` when it produces such expressions, so you
can decide whether the behavior matches your intent.

## Advanced: Direct Dataclass Access

```python
from recronslator.model import ScheduleIntent, CronExpression
from recronslator.compiler import compile_intent
from recronslator.validator import validate_intent

intent = ScheduleIntent(
    minute_interval=15,
    hour_range=(9, 17),
    weekday_only=True,
)
validate_intent(intent)
expr = compile_intent(intent)
print(expr)  # */15 9-17 * * 1-5
```

## Requirements

- Python 3.10+
- No runtime dependencies (standard library only)

## Development

```bash
git clone <repo>
cd recronslator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=recronslator --cov-report=term-missing

# Type checking
mypy src/
```

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Based on the original [pyslop/cronslator](https://github.com/pyslop/cronslator)
project (CC0 license), which demonstrated what Copilot can generate from prompts alone.
`recronslator` is a human-directed rewrite that fixes the correctness issues and
adds a proper architecture and test suite.
