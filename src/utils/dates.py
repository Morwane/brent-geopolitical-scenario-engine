"""Date and time utilities."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def trading_days_range(start: str, end: str) -> pd.DatetimeIndex:
    """Return a business-day DatetimeIndex between start and end (inclusive)."""
    return pd.bdate_range(start=start, end=end)


def offset_date(d: str | date, offset_days: int) -> str:
    """Return a date string offset by N calendar days."""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return (d + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def last_n_years(n: int = 5) -> tuple[str, str]:
    """Return (start, end) date strings for the last N years."""
    end = date.today()
    start = end.replace(year=end.year - n)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def parse_date(d: str | date | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(d)
