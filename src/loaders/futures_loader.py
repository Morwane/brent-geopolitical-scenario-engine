"""
Brent futures curve loader.

Confirmed accessible (smoke test 2026-04-21):
  LCOc1 through LCOc12 — all via TRDPRC_1

Assembles all accessible maturities into a single aligned DataFrame
for curve and calendar spread analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.discovery import get_curve_rics, get_primary_brent_ric

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"


def _fetch_one(ric: str, field: str, start: str, end: str) -> pd.Series:
    try:
        import lseg.data as ld  # type: ignore

        df = ld.get_history(universe=ric, fields=[field], start=start, end=end)
        if df is None or df.empty or field not in df.columns:
            logger.warning("Empty response: %s / %s", ric, field)
            return pd.Series(dtype=float, name=ric)
        s = df[field].dropna()
        s.index = pd.to_datetime(s.index)
        s.name = ric
        return s
    except Exception as exc:
        logger.error("Fetch failed %s: %s", ric, exc)
        return pd.Series(dtype=float, name=ric)


def load_curve(
    start: str,
    end: str,
    save: bool = True,
) -> pd.DataFrame:
    """Load all accessible Brent maturities into a single curve DataFrame.

    Columns are named by RIC (e.g. LCOc1, LCOc2, …, LCOc12).
    Only maturities confirmed accessible in the inventory are included.

    Parameters
    ----------
    start, end : YYYY-MM-DD
    save       : write to data/processed/curve.parquet and .csv

    Returns
    -------
    pd.DataFrame — RIC columns, date index. Empty if nothing accessible.
    """
    primary_ric, primary_field = get_primary_brent_ric()
    curve_rics = get_curve_rics()

    # Build ordered list of (ric, field), primary first, then deferred maturities
    all_pairs: list[tuple[str, str]] = [(primary_ric, primary_field)]
    seen = {primary_ric}
    for r in curve_rics:
        if r["ric"] not in seen:
            all_pairs.append((r["ric"], r["working_field"]))
            seen.add(r["ric"])

    if not all_pairs:
        logger.warning("No accessible Brent RICs in inventory — returning empty curve.")
        return pd.DataFrame()

    logger.info("Loading Brent curve: %s [%s to %s]", [r for r, _ in all_pairs], start, end)

    series = []
    for ric, field in all_pairs:
        s = _fetch_one(ric, field, start, end)
        if not s.empty:
            series.append(s)
        else:
            logger.warning("  %s returned empty — excluded from curve.", ric)

    if not series:
        return pd.DataFrame()

    df = pd.concat(series, axis=1)
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df = df.sort_index()

    _log_quality(df)

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(PROCESSED_DIR / "curve.parquet")
        df.to_csv(PROCESSED_DIR / "curve.csv")
        logger.info("Saved → data/processed/curve.parquet")

    return df


def load_curve_from_file() -> pd.DataFrame:
    """Load previously saved curve (fallback when LSEG is unavailable)."""
    for p in [PROCESSED_DIR / "curve.parquet", PROCESSED_DIR / "curve.csv"]:
        if p.exists():
            return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(
                p, index_col=0, parse_dates=True
            )
    raise FileNotFoundError("No cached curve. Run load_curve() with a live session.")


def _log_quality(df: pd.DataFrame) -> None:
    logger.info("[curve] rows=%d  range=%s → %s  columns=%s",
                len(df),
                df.index.min().date() if not df.empty else "N/A",
                df.index.max().date() if not df.empty else "N/A",
                list(df.columns))
    for col in df.columns:
        miss = int(df[col].isna().sum())
        logger.info("  %s: %d missing", col, miss)
