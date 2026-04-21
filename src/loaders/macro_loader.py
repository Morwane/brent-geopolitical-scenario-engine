"""
Macro / risk proxy loader.

Confirmed accessible (discovery 2026-04-21):
  .SPX (S&P 500)  — TRDPRC_1  ✅
  DXY             — NOT accessible in this environment
  US10YT=RR       — NOT accessible in this environment

Macro data is OPTIONAL enrichment. If nothing is accessible, the module
returns an empty DataFrame and logs a clear warning. No core module
hard-depends on macro data being present.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.discovery import get_accessible_rics

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
MACRO_PATH = PROCESSED_DIR / "macro.parquet"


def _fetch_one(ric: str, field: str, start: str, end: str, label: str) -> pd.Series:
    try:
        import lseg.data as ld  # type: ignore

        df = ld.get_history(universe=ric, fields=[field], start=start, end=end)
        if df is None or df.empty or field not in df.columns:
            return pd.Series(dtype=float, name=label)
        s = df[field].dropna()
        s.index = pd.to_datetime(s.index)
        s.name = label
        return s
    except Exception as exc:
        logger.warning("Macro fetch failed %s: %s", ric, exc)
        return pd.Series(dtype=float, name=label)


def load_macro(
    start: str,
    end: str,
    save: bool = True,
) -> pd.DataFrame:
    """Load accessible macro / risk proxy instruments.

    Returns an empty DataFrame (not an error) if none are available.

    Parameters
    ----------
    start, end : YYYY-MM-DD
    save       : write non-empty result to data/processed/macro.parquet

    Returns
    -------
    pd.DataFrame — columns named by instrument label. Empty if none accessible.
    """
    try:
        macro_rics = get_accessible_rics(group="macro_proxies")
    except Exception:
        logger.warning("Could not load macro inventory — skipping macro.")
        return pd.DataFrame()

    if not macro_rics:
        logger.warning(
            "No macro instruments in inventory — macro context unavailable. "
            "This is acceptable; the core pipeline runs without macro data."
        )
        return pd.DataFrame()

    series: list[pd.Series] = []
    for rec in macro_rics:
        ric = rec["ric"]
        field = rec.get("working_field") or "TRDPRC_1"
        label = rec.get("label", ric)
        logger.info("Loading macro: %s (%s)...", label, ric)
        s = _fetch_one(ric, field, start, end, label)
        if not s.empty:
            series.append(s)
            logger.info("  -> %d rows", len(s))
        else:
            logger.info("  -> empty (skipped)")

    if not series:
        logger.warning("All macro fetches empty.")
        return pd.DataFrame()

    df = pd.concat(series, axis=1)
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df = df.sort_index()

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(MACRO_PATH)
        df.to_csv(MACRO_PATH.with_suffix(".csv"))
        logger.info("Saved → data/processed/macro.parquet")

    return df


def load_macro_from_file() -> pd.DataFrame:
    """Load previously saved macro data. Returns empty DataFrame if not found."""
    for p in [MACRO_PATH, MACRO_PATH.with_suffix(".csv")]:
        if p.exists():
            return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(
                p, index_col=0, parse_dates=True
            )
    logger.info("No macro cache found — returning empty frame (expected if macro unavailable).")
    return pd.DataFrame()
