"""
News-based geopolitical shock score.

Transparent keyword-counting approach — economic logic is explicit.
Score components:
  escalation_hits     : escalation keyword matches per day
  de_escalation_hits  : de-escalation keyword matches per day
  net_score           : escalation_hits - de_escalation_hits
  smooth_score        : rolling mean of net_score
  geo_shock_score     : rolling z-score of smooth_score (0-centred, comparable across time)

This baseline must exist before any NLP enhancements are considered.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ESCALATION_KEYWORDS = [
    "attack", "strike", "military", "missile", "drone", "blockade",
    "closure", "seized", "seized tanker", "explosion", "tensions",
    "escalation", "sanctions", "threat", "airstrikes", "conflict",
    "war", "IRGC", "proxy", "retaliation", "bombing", "assassination",
]

DE_ESCALATION_KEYWORDS = [
    "ceasefire", "de-escalation", "deal", "agreement", "talks",
    "diplomacy", "diplomatic", "negotiations", "withdrawal", "truce",
    "release", "prisoner swap", "JCPOA", "nuclear deal", "sanctions relief",
    "confidence-building", "resumption", "dialogue",
]


def _count_hits(text: str, keywords: list[str]) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw.lower() in t)


def score_headlines(headlines: pd.DataFrame) -> pd.DataFrame:
    """Add escalation_hits and de_escalation_hits columns to a headlines DataFrame."""
    if "headline" not in headlines.columns:
        raise ValueError("headlines DataFrame must have a 'headline' column.")
    df = headlines.copy()
    df["escalation_hits"] = df["headline"].apply(
        lambda t: _count_hits(str(t), ESCALATION_KEYWORDS)
    )
    df["de_escalation_hits"] = df["headline"].apply(
        lambda t: _count_hits(str(t), DE_ESCALATION_KEYWORDS)
    )
    return df


def build_daily_geo_score(
    headlines: pd.DataFrame,
    smoothing_window: int = 5,
    zscore_window: int = 63,
) -> pd.DataFrame:
    """Aggregate scored headlines to a daily geo shock score.

    Parameters
    ----------
    headlines        : DataFrame with 'date' and 'headline' columns
    smoothing_window : rolling mean window applied before z-scoring
    zscore_window    : lookback window for rolling z-score

    Returns
    -------
    pd.DataFrame — date index, columns:
        escalation_hits, de_escalation_hits, net_score, smooth_score, geo_shock_score
    """
    if "date" not in headlines.columns:
        raise ValueError("headlines must have a 'date' column.")

    scored = score_headlines(headlines) if "escalation_hits" not in headlines.columns else headlines.copy()
    scored["date"] = pd.to_datetime(scored["date"]).dt.normalize()

    daily = (
        scored.groupby("date")[["escalation_hits", "de_escalation_hits"]]
        .sum()
        .sort_index()
    )
    daily["net_score"] = daily["escalation_hits"] - daily["de_escalation_hits"]
    daily["smooth_score"] = daily["net_score"].rolling(smoothing_window, min_periods=1).mean()

    roll_mean = daily["smooth_score"].rolling(zscore_window, min_periods=10).mean()
    roll_std  = daily["smooth_score"].rolling(zscore_window, min_periods=10).std().replace(0, np.nan)
    daily["geo_shock_score"] = (daily["smooth_score"] - roll_mean) / roll_std

    logger.info(
        "[geo_score] %d days scored | non-null score: %d",
        len(daily), int(daily["geo_shock_score"].notna().sum()),
    )
    return daily


def align_to_prices(
    geo_score: pd.DataFrame,
    price_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Reindex geo score to match the price series index.

    Days with no news are forward-filled — geopolitical background does not
    reset to zero on quiet headline days.
    """
    return geo_score.reindex(price_index).ffill()
