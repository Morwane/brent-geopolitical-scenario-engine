"""
Brent and WTI daily price loader.

Confirmed accessible (smoke test 2026-04-21):
  LCOc1 (Brent M1) — TRDPRC_1
  CLc1  (WTI M1)   — TRDPRC_1

Validates, cleans, aligns, and saves to data/processed/prices.parquet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.discovery import get_primary_brent_ric, get_wti_ric

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"


def _fetch(ric: str, field: str, start: str, end: str) -> pd.Series:
    try:
        import lseg.data as ld  # type: ignore

        df = ld.get_history(universe=ric, fields=[field], start=start, end=end)
        if df is None or df.empty or field not in df.columns:
            logger.warning("Empty response: %s / %s", ric, field)
            return pd.Series(dtype=float, name=ric)
        s = df[field].dropna()
        s.index = pd.to_datetime(s.index)
        s.name = ric
        logger.info("  %s: %d rows [%s → %s]", ric, len(s), s.index.min().date(), s.index.max().date())
        return s
    except Exception as exc:
        logger.error("Fetch failed %s: %s", ric, exc)
        return pd.Series(dtype=float, name=ric)


def load_prices(
    start: str,
    end: str,
    save: bool = True,
) -> pd.DataFrame:
    """Load Brent (LCOc1) and WTI (CLc1) daily close prices.

    Parameters
    ----------
    start, end : YYYY-MM-DD
    save       : write result to data/processed/prices.parquet and .csv

    Returns
    -------
    pd.DataFrame — columns: brent, wti. Date index. NaN where unavailable.
    """
    brent_ric, brent_field = get_primary_brent_ric()
    wti_ric, wti_field = get_wti_ric()

    logger.info("Loading prices [%s to %s]", start, end)
    brent = _fetch(brent_ric, brent_field, start, end).rename("brent")
    wti   = _fetch(wti_ric, wti_field, start, end).rename("wti")

    df = pd.concat([brent, wti], axis=1)
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df = df.sort_index()

    _log_quality(df, "prices")

    if save:
        _save(df, "prices")

    return df


def load_prices_from_file() -> pd.DataFrame:
    """Load previously saved prices (fallback when LSEG is unavailable)."""
    for p in [PROCESSED_DIR / "prices.parquet", PROCESSED_DIR / "prices.csv"]:
        if p.exists():
            logger.info("Loading prices from cache: %s", p)
            return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(
                p, index_col=0, parse_dates=True
            )
    raise FileNotFoundError("No cached prices. Run load_prices() with a live session.")


def _log_quality(df: pd.DataFrame, label: str) -> None:
    logger.info("[%s] rows=%d  range=%s → %s", label, len(df),
                df.index.min().date() if not df.empty else "N/A",
                df.index.max().date() if not df.empty else "N/A")
    for col in df.columns:
        miss = int(df[col].isna().sum())
        logger.info("  %s: %d missing (%.1f%%)", col, miss, 100 * miss / max(len(df), 1))


def _save(df: pd.DataFrame, stem: str) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_DIR / f"{stem}.parquet")
    df.to_csv(PROCESSED_DIR / f"{stem}.csv")
    logger.info("Saved → data/processed/%s.parquet", stem)
