"""Input validation helpers for loader and analytics modules."""

from __future__ import annotations

import pandas as pd


def require_columns(df: pd.DataFrame, cols: list[str], name: str = "DataFrame") -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def require_date_index(df: pd.DataFrame, name: str = "DataFrame") -> None:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(f"{name} must have a DatetimeIndex.")


def check_min_rows(df: pd.DataFrame, min_rows: int = 10, name: str = "DataFrame") -> bool:
    if len(df) < min_rows:
        import warnings
        warnings.warn(
            f"{name} has only {len(df)} rows (expected >= {min_rows}). "
            "Results may be unreliable.",
            stacklevel=2,
        )
        return False
    return True


def assert_series_aligned(*series: pd.Series) -> None:
    """Raise ValueError if any two series have incompatible date indices."""
    indices = [s.index for s in series if not s.empty]
    if len(indices) < 2:
        return
    ref = indices[0]
    for idx in indices[1:]:
        if not ref.equals(idx):
            raise ValueError(
                "Series have misaligned date indices. "
                "Use pd.concat or reindex to align before passing to analytics functions."
            )
