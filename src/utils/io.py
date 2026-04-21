"""I/O helpers: save/load DataFrames in parquet and CSV formats."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def save_df(df: pd.DataFrame, path: str | Path, also_csv: bool = True) -> None:
    """Save a DataFrame to Parquet (and optionally CSV)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p = p.with_suffix(".parquet")
    df.to_parquet(p)
    logger.info("Saved → %s", p)
    if also_csv:
        csv_p = p.with_suffix(".csv")
        df.to_csv(csv_p)
        logger.debug("Also saved CSV → %s", csv_p)


def load_df(path: str | Path) -> pd.DataFrame:
    """Load a DataFrame from Parquet or CSV based on file extension."""
    p = Path(path)
    if not p.exists():
        parquet_p = p.with_suffix(".parquet")
        csv_p     = p.with_suffix(".csv")
        if parquet_p.exists():
            p = parquet_p
        elif csv_p.exists():
            p = csv_p
        else:
            raise FileNotFoundError(f"No file found at {path} (tried .parquet and .csv)")
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    return pd.read_csv(p, index_col=0, parse_dates=True)
