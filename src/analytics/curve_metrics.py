"""
Brent curve structure diagnostics.

Classifies daily curve state (backwardation / contango) and computes
slope and rolling structure metrics where sufficient maturities are available.

Pure functions — no I/O.
"""

from __future__ import annotations

import pandas as pd


def curve_slope(
    curve: pd.DataFrame,
    front_col: str = "LCOc1",
    back_col: str = "LCOc6",
) -> pd.Series:
    """Annualised slope: (back - front) / months_between.

    Positive = contango. Negative = backwardation.
    """
    def _month(col: str) -> int:
        for prefix in ("LCOc", "CLc"):
            if col.startswith(prefix):
                try:
                    return int(col[len(prefix):])
                except ValueError:
                    pass
        return 1

    gap = _month(back_col) - _month(front_col)
    if gap <= 0:
        raise ValueError(f"{back_col} must have later maturity than {front_col}.")
    for col in (front_col, back_col):
        if col not in curve.columns:
            raise KeyError(f"Column '{col}' not in curve DataFrame.")
    return ((curve[back_col] - curve[front_col]) / gap).rename(f"slope_{front_col}_{back_col}")


def classify_curve_structure(
    spread_m1_near: pd.Series,
    threshold: float = 0.0,
) -> pd.Series:
    """Classify each day as 'backwardation' or 'contango'.

    Parameters
    ----------
    spread_m1_near : M1-M2 or M1-M3 calendar spread
    threshold      : spread above this → backwardation
    """
    s = pd.Series(index=spread_m1_near.index, dtype=object)
    s[spread_m1_near > threshold] = "backwardation"
    s[spread_m1_near <= threshold] = "contango"
    s[spread_m1_near.isna()] = pd.NA
    return s.rename("curve_structure")


def rolling_backwardation_pct(spread: pd.Series, window: int = 21) -> pd.Series:
    """Rolling % of days in backwardation over the given window."""
    return (spread > 0).astype(float).rolling(window).mean().rename(f"pct_back_{window}d")


def compute_curve_metrics(
    curve: pd.DataFrame,
    spreads: pd.DataFrame,
) -> pd.DataFrame:
    """Build curve structure metrics from whatever maturities are available."""
    metrics: dict[str, pd.Series] = {}

    # Slope — try best available pair
    for front, back in [("LCOc1", "LCOc6"), ("LCOc1", "LCOc3"), ("LCOc1", "LCOc2")]:
        if front in curve.columns and back in curve.columns:
            try:
                metrics["curve_slope"] = curve_slope(curve, front, back)
                break
            except Exception:
                continue

    # Structure classification — use M1_M3 > M1_M2 > M1_M6
    for col in ["M1_M3", "M1_M2", "M1_M6"]:
        if col in spreads.columns:
            metrics["curve_structure"] = classify_curve_structure(spreads[col])
            metrics["pct_back_21d"] = rolling_backwardation_pct(spreads[col], 21)
            metrics["pct_back_63d"] = rolling_backwardation_pct(spreads[col], 63)
            break

    return pd.DataFrame(metrics) if metrics else pd.DataFrame(index=curve.index)


def summarise_curve_regimes(curve_metrics: pd.DataFrame) -> pd.DataFrame:
    if "curve_structure" not in curve_metrics.columns:
        return pd.DataFrame()
    counts = curve_metrics["curve_structure"].value_counts()
    pct = (counts / counts.sum() * 100).round(1)
    return pd.DataFrame({"count": counts, "pct_%": pct})
