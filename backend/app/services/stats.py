"""Small helpers for dashboard numbers.

Month buckets are computed in Python so they behave the same on SQLite and Postgres.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal


def as_utc(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat them as UTC like Postgres does."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def now_utc() -> datetime:
    return datetime.now(UTC)


def month_key(value: datetime) -> tuple[int, int]:
    value = as_utc(value)
    return value.year, value.month


def last_months(count: int = 8, today: datetime | None = None) -> list[tuple[int, int]]:
    """The last `count` (year, month) pairs, oldest first, ending with the current month."""
    today = today or now_utc()
    year, month = today.year, today.month
    keys = []
    for _ in range(count):
        keys.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return keys[::-1]


MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly_series(rows: Iterable[tuple[datetime, Decimal | float | int]], count: int = 8) -> list[dict]:
    """[(when, amount), ...] -> [{label: 'Jan', value: 1234.0}, ...] for the last `count` months."""
    totals: dict[tuple[int, int], float] = defaultdict(float)
    for when, amount in rows:
        totals[month_key(when)] += float(amount)
    return [{"label": MONTH_LABELS[m - 1], "value": round(totals[(y, m)], 2)} for y, m in last_months(count)]


def growth(current: float, previous: float) -> float | None:
    """Percent change versus the previous period, or None when there is nothing to compare with."""
    if not previous:
        return None
    return round(100 * (current - previous) / previous, 1)


def this_and_last_month(rows: Iterable[tuple[datetime, Decimal | float | int]]) -> tuple[float, float]:
    keys = last_months(2)
    totals: dict[tuple[int, int], float] = defaultdict(float)
    for when, amount in rows:
        totals[month_key(when)] += float(amount)
    return totals[keys[1]], totals[keys[0]]
