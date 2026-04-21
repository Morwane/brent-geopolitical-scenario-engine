"""
Calendar spread and cross-market spread calculations.

Spreads computed:
  M1_M2   = LCOc1 - LCOc2
  M1_M3   = LCOc1 - LCOc3
  M1_M6   = LCOc1 - LCOc6
  M6_M12  = LCOc6 - LCOc12
  brent_wti = brent - wti

Positive = backwardation (prompt premium over deferred).
Negative = contango.

All functions are pure — no I/O, no session dependency.
"""

from __future__ import annotations

import pandas as pd

# Map spread label → (near_ric, far_ric) in the curve DataFrame
SPREAD_DEFINITIONS: dict[str, tuple[str, str]] = {
    "M1_M2":  ("LCOc1", "LCOc2"),
    "M1_M3":  ("LCOc1", "LCOc3"),
    "M1_M6":  ("LCOc1", "LCOc6"),
    "M6_M12": ("LCOc6", "LCOc12"),
}


def calendar_spread(
    curve: pd.DataFrame,
    near_col: str,
    far_col: str,
    label: str | None = None,
) -> pd.Series:
    """Compute near - far. Returns NaN where either leg is missing."""
    for col in (near_col, far_col):
        if col not in curve.columns:
            raise KeyError(
                f"Column '{col}' not in curve DataFrame. "
                "Check discovery validated both maturities."
            )
    return (curve[near_col] - curve[far_col]).rename(label or f"{near_col}_{far_col}")


def compute_all_calendar_spreads(
    curve: pd.DataFrame,
    definitions: dict[str, tuple[str, str]] | None = None,
    skip_missing: bool = True,
) -> pd.DataFrame:
    """Compute all calendar spreads from the curve DataFrame.

    Skips any spread whose legs are not present (skip_missing=True default).
    """
    definitions = definitions or SPREAD_DEFINITIONS
    result: dict[str, pd.Series] = {}
    for label, (near, far) in definitions.items():
        if near not in curve.columns or far not in curve.columns:
            if not skip_missing:
                raise KeyError(f"Missing columns for spread {label}: {near}, {far}")
            continue
        result[label] = calendar_spread(curve, near, far, label)
    return pd.DataFrame(result) if result else pd.DataFrame(index=curve.index)


def brent_wti_spread(
    prices: pd.DataFrame,
    brent_col: str = "brent",
    wti_col: str = "wti",
) -> pd.Series:
    """Brent - WTI spread. Positive = Brent premium."""
    for col in (brent_col, wti_col):
        if col not in prices.columns:
            raise KeyError(f"Column '{col}' not in prices DataFrame.")
    return (prices[brent_col] - prices[wti_col]).rename("brent_wti")


def build_spread_panel(
    prices: pd.DataFrame,
    curve: pd.DataFrame,
    skip_missing: bool = True,
) -> pd.DataFrame:
    """Assemble all spreads into one aligned panel DataFrame."""
    frames: list[pd.DataFrame] = []
    cal = compute_all_calendar_spreads(curve, skip_missing=skip_missing)
    if not cal.empty:
        frames.append(cal)
    if "brent" in prices.columns and "wti" in prices.columns:
        frames.append(brent_wti_spread(prices).to_frame())
    if not frames:
        return pd.DataFrame()
    panel = pd.concat(frames, axis=1)
    panel.index.name = "date"
    return panel.sort_index()


def spread_summary_stats(spreads: pd.DataFrame) -> pd.DataFrame:
    """Descriptive statistics per spread: mean, std, min, p25, p50, p75, max, pct_backwardation."""
    records = []
    for col in spreads.columns:
        s = spreads[col].dropna()
        records.append({
            "spread": col,
            "mean": round(s.mean(), 3),
            "std":  round(s.std(), 3),
            "min":  round(s.min(), 3),
            "p25":  round(s.quantile(0.25), 3),
            "p50":  round(s.quantile(0.50), 3),
            "p75":  round(s.quantile(0.75), 3),
            "max":  round(s.max(), 3),
            "pct_backwardation": round(float((s > 0).mean()), 3),
        })
    return pd.DataFrame(records).set_index("spread")
