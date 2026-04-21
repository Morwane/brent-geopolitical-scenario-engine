"""
Event study engine — core analytical method.

Implements a standard finance event study for geopolitical events:
  - Event window: pre-event estimation period, event day, post-event horizons
  - Abnormal return = actual return − mean of estimation window
  - CAR (Cumulative Abnormal Return) summed over post-event windows
  - Summary tables by event direction (escalation / de-escalation)

Methodology: Brown & Warner (1985), standard commodity event study practice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class Event:
    date: pd.Timestamp
    label: str
    category: str = ""
    description: str = ""
    direction: str = ""   # "escalation" | "de-escalation" | "neutral"


@dataclass
class EventStudyConfig:
    pre_event_days: int = 20
    post_event_windows: list[int] = field(default_factory=lambda: [1, 3, 5, 10])


def load_events_from_csv(path: str) -> list[Event]:
    """Load events from CSV with columns: date, label, category, description, direction."""
    df = pd.read_csv(path, parse_dates=["date"])
    return [
        Event(
            date=pd.Timestamp(row["date"]),
            label=str(row.get("label", "")),
            category=str(row.get("category", "")),
            description=str(row.get("description", "")),
            direction=str(row.get("direction", "")),
        )
        for _, row in df.iterrows()
    ]


def _normal_return(returns: pd.Series, event_date: pd.Timestamp, window: int) -> float:
    """Mean return over the pre-event estimation window."""
    idx = returns.index.get_indexer([event_date], method="pad")[0]
    if idx < window or idx < 0:
        return float("nan")
    return float(returns.iloc[idx - window : idx].mean())


def _cumulative_return(
    returns: pd.Series, event_date: pd.Timestamp, horizons: Sequence[int]
) -> dict[str, float]:
    """Sum of returns from event day through each horizon."""
    idx = returns.index.get_indexer([event_date], method="pad")[0]
    result: dict[str, float] = {}
    for h in horizons:
        end = idx + h
        if idx < 0 or end >= len(returns):
            result[f"ret_{h}d"] = float("nan")
        else:
            result[f"ret_{h}d"] = float(returns.iloc[idx : end + 1].sum())
    return result


def run_event_study(
    returns: pd.Series,
    events: list[Event],
    config: EventStudyConfig | None = None,
    series_label: str = "brent",
) -> pd.DataFrame:
    """Run event study for one return series against a list of events.

    Returns one row per event with columns:
      event_date, label, category, direction,
      {label}_ret_{h}d, {label}_car_{h}d for each horizon h.
    """
    cfg = config or EventStudyConfig()
    records = []

    for ev in events:
        normal = _normal_return(returns, ev.date, cfg.pre_event_days)
        cum_rets = _cumulative_return(returns, ev.date, cfg.post_event_windows)

        row: dict = {
            "event_date": ev.date,
            "label": ev.label,
            "category": ev.category,
            "direction": ev.direction,
            f"normal_ret_{series_label}": normal,
        }
        for h in cfg.post_event_windows:
            raw = cum_rets.get(f"ret_{h}d", float("nan"))
            row[f"{series_label}_ret_{h}d"] = raw
            if not (np.isnan(raw) or np.isnan(normal)):
                row[f"{series_label}_car_{h}d"] = raw - h * normal
            else:
                row[f"{series_label}_car_{h}d"] = float("nan")

        records.append(row)

    return pd.DataFrame(records)


def run_multi_series_event_study(
    series_dict: dict[str, pd.Series],
    events: list[Event],
    config: EventStudyConfig | None = None,
) -> pd.DataFrame:
    """Run event study across multiple series (Brent, spreads, Brent-WTI) and merge.

    Parameters
    ----------
    series_dict : {label: return_series} e.g. {"brent": ..., "M1_M3": ..., "brent_wti": ...}

    Returns merged wide DataFrame, one row per event.
    """
    cfg = config or EventStudyConfig()
    parts: list[pd.DataFrame] = []

    for i, (label, ret_series) in enumerate(series_dict.items()):
        df = run_event_study(ret_series, events, cfg, series_label=label)
        if i == 0:
            parts.append(df)
        else:
            meta = ["event_date", "label", "category", "direction"]
            parts.append(df.drop(columns=meta, errors="ignore"))

    return pd.concat(parts, axis=1) if parts else pd.DataFrame()


def summary_by_direction(
    es_df: pd.DataFrame,
    col: str,
) -> pd.DataFrame:
    """Aggregate event study results by direction with t-test significance.

    Returns DataFrame with columns: n_events, mean_car, std_car, t_stat, p_value.
    """
    if col not in es_df.columns or "direction" not in es_df.columns:
        return pd.DataFrame()
    records = []
    for direction, grp in es_df.groupby("direction"):
        vals = grp[col].dropna()
        n = len(vals)
        mean = vals.mean()
        std = vals.std()
        t, p = stats.ttest_1samp(vals, 0.0) if n > 1 else (float("nan"), float("nan"))
        records.append({
            "direction": direction, "n_events": n,
            "mean_car": round(mean, 4), "std_car": round(std, 4),
            "t_stat": round(t, 3), "p_value": round(p, 4),
        })
    return pd.DataFrame(records).set_index("direction")


def average_event_profile(
    es_df: pd.DataFrame,
    horizons: list[int] | None = None,
    col_prefix: str = "brent_car",
    direction_filter: str | None = None,
) -> pd.DataFrame:
    """Compute mean CAR profile across events at each horizon.

    Returns DataFrame indexed by horizon_d with columns: mean_car, std_car, n.
    """
    horizons = horizons or [1, 3, 5, 10]
    df = es_df if not direction_filter else es_df[es_df["direction"] == direction_filter]
    records = []
    for h in horizons:
        col = f"{col_prefix}_{h}d"
        if col not in df.columns:
            continue
        vals = df[col].dropna()
        records.append({
            "horizon_d": h,
            "mean_car": vals.mean(),
            "std_car": vals.std(),
            "n": len(vals),
        })
    return pd.DataFrame(records).set_index("horizon_d")
