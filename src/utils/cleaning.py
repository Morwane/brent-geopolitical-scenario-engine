"""Data cleaning helpers."""

from __future__ import annotations

import pandas as pd


def drop_leading_trailing_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where ALL columns are NaN from the start and end of the DataFrame."""
    mask = df.notna().any(axis=1)
    first = mask.idxmax()
    last  = mask[::-1].idxmax()
    return df.loc[first:last]


def fill_weekend_gaps(series: pd.Series, method: str = "ffill") -> pd.Series:
    """Forward- or backward-fill missing values (weekends / holidays)."""
    return series.fillna(method=method)  # type: ignore[arg-type]


def align_to_business_days(
    df: pd.DataFrame,
    start: str,
    end: str,
    fill_method: str = "ffill",
) -> pd.DataFrame:
    """Reindex DataFrame to business days and fill gaps."""
    bdays = pd.bdate_range(start=start, end=end)
    return df.reindex(bdays).fillna(method=fill_method)  # type: ignore[arg-type]


def remove_outliers_iqr(
    series: pd.Series,
    multiplier: float = 3.0,
) -> pd.Series:
    """Replace values beyond ±multiplier × IQR with NaN."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    mask = (series < q1 - multiplier * iqr) | (series > q3 + multiplier * iqr)
    result = series.copy()
    result[mask] = float("nan")
    return result
