"""
Instrument and field discovery.

CONSERVATIVE BY DESIGN.

Smoke test baseline (2026-04-21, lseg.data 2.1.1, local Workspace session):
  CONFIRMED accessible via TRDPRC_1:
    LCOc1 (Brent M1)  — 20 rows
    LCOc2 (Brent M2)  — 20 rows
    LCOc3 (Brent M3)  — 20 rows
    CLc1  (WTI M1)    — 21 rows
  NOT YET TESTED:
    LCOc6, LCOc12, macro proxies (DXY, US10YT=RR, .SPX)

This module must be run before any loader pulls a full date range.
It produces data/processed/instrument_inventory.csv, which all loaders
read to determine which RICs and fields to use.

Run manually::

    python -m src.discovery
    python -m src.discovery 2025-01-01 2025-01-20   # optional date override
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "instruments.yaml"
FIELDS_CONFIG_PATH = ROOT / "config" / "fields.yaml"
INVENTORY_PATH = ROOT / "data" / "processed" / "instrument_inventory.csv"

_MIN_NON_NULL = 3


def _default_probe_window() -> tuple[str, str]:
    today = date.today()
    return (
        (today - timedelta(days=30)).strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
    )


def _load_instruments() -> dict[str, list[dict[str, Any]]]:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return {
        "brent_futures": cfg.get("brent_futures", []),
        "wti_futures": cfg.get("wti_futures", []),
        "macro_proxies": cfg.get("macro_proxies", []),
    }


def _candidate_fields() -> list[str]:
    try:
        with open(FIELDS_CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        return cfg.get("price_field_priority", ["TRDPRC_1", "CLOSE"])
    except Exception:
        return ["TRDPRC_1", "CLOSE"]


def _probe_field(ric: str, field: str, start: str, end: str) -> bool:
    """Return True if the field returns >= _MIN_NON_NULL rows for the RIC."""
    try:
        import lseg.data as ld  # type: ignore

        df = ld.get_history(universe=ric, fields=[field], start=start, end=end)
        if df is None or df.empty or field not in df.columns:
            return False
        return int(df[field].notna().sum()) >= _MIN_NON_NULL
    except Exception as exc:
        logger.debug("Probe failed — %s / %s: %s", ric, field, exc)
        return False


def _find_working_field(
    ric: str,
    candidate_fields: list[str],
    start: str,
    end: str,
) -> str | None:
    """Try each field in priority order; return first that works, or None."""
    for field in candidate_fields:
        if _probe_field(ric, field, start, end):
            return field
    return None


def _probe_news_access() -> bool:
    """Return True if LSEG news headline search returns any results."""
    try:
        import lseg.data as ld  # type: ignore

        results = ld.news.get_headlines(query="Iran oil", count=5)
        return results is not None and not results.empty
    except Exception as exc:
        logger.debug("News probe failed: %s", exc)
        return False


def discover_instruments(
    start: str | None = None,
    end: str | None = None,
    probe_news: bool = True,
) -> pd.DataFrame:
    """Probe all candidate instruments and return a validated inventory DataFrame.

    Instruments confirmed in the smoke test will be skipped if their
    validated=true flag is already set in instruments.yaml, unless the
    date range forces a re-probe.

    Parameters
    ----------
    start, end  : YYYY-MM-DD probe window. Defaults to last 30 days.
    probe_news  : also probe news headline access (recorded separately).

    Returns
    -------
    pd.DataFrame with columns:
        ric, label, role, group, accessible, working_field, notes
    """
    default_start, default_end = _default_probe_window()
    start = start or default_start
    end = end or default_end

    fields = _candidate_fields()
    groups = _load_instruments()

    records: list[dict[str, Any]] = []

    for group_name, instruments in groups.items():
        for inst in instruments:
            ric = inst["ric"]
            label = inst.get("label", ric)
            role = inst.get("role", "unknown")
            notes = inst.get("fallback_note", "")
            pre_validated = inst.get("validated", False)
            pre_field = inst.get("working_field")

            # If already validated in config and we trust the config, skip probe
            if pre_validated and pre_field:
                logger.info("%-8s  SKIPPED (pre-validated: field=%s)", ric, pre_field)
                records.append({
                    "ric": ric, "label": label, "role": role, "group": group_name,
                    "accessible": True, "working_field": pre_field, "notes": notes,
                })
                continue

            logger.info("%-8s  Probing (%s)...", ric, label)
            wf = _find_working_field(ric, fields, start, end)
            accessible = wf is not None
            status = "OK" if accessible else "UNAVAILABLE"
            logger.info("%-8s  %s  field=%s", ric, status, wf or "none")

            records.append({
                "ric": ric, "label": label, "role": role, "group": group_name,
                "accessible": accessible, "working_field": wf, "notes": notes,
            })

    df = pd.DataFrame(records)

    if probe_news:
        news_ok = _probe_news_access()
        logger.info("News API accessible: %s", news_ok)
        # Store as a metadata record for reference
        df = pd.concat([
            df,
            pd.DataFrame([{
                "ric": "_news_api",
                "label": "LSEG News Headlines API",
                "role": "news",
                "group": "news",
                "accessible": news_ok,
                "working_field": "ld.news.get_headlines" if news_ok else None,
                "notes": "Tested via ld.news.get_headlines(query='Iran oil', count=5)",
            }])
        ], ignore_index=True)

    return df


def save_inventory(df: pd.DataFrame, path: Path | None = None) -> None:
    path = path or INVENTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Inventory saved → %s", path)


def load_inventory(path: Path | None = None) -> pd.DataFrame:
    """Load the saved instrument inventory.

    Raises FileNotFoundError if no inventory exists — run src/discovery.py first.
    Always filter to accessible==True before using any RIC in production code.
    """
    path = path or INVENTORY_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"No inventory at {path}.\n"
            "Run:  python -m src.discovery"
        )
    df = pd.read_csv(path)
    df["accessible"] = df["accessible"].astype(bool)
    return df


def get_accessible_rics(
    group: str | None = None,
    role: str | None = None,
    path: Path | None = None,
) -> list[dict[str, str]]:
    """Return accessible RIC records, optionally filtered by group and role."""
    df = load_inventory(path)
    df = df[df["accessible"] & (df["ric"] != "_news_api")]
    if group:
        df = df[df["group"] == group]
    if role:
        df = df[df["role"] == role]
    return df[["ric", "label", "role", "group", "working_field"]].to_dict("records")


def get_primary_brent_ric(path: Path | None = None) -> tuple[str, str]:
    """Return (ric, working_field) for the primary Brent instrument.

    Falls back to (LCOc1, TRDPRC_1) — the smoke-test confirmed default —
    if no inventory exists yet.
    """
    try:
        records = get_accessible_rics(group="brent_futures", role="primary", path=path)
        if records:
            return records[0]["ric"], records[0]["working_field"]
    except FileNotFoundError:
        logger.warning("No inventory — using smoke-test default: LCOc1 / TRDPRC_1.")
    return "LCOc1", "TRDPRC_1"


def get_wti_ric(path: Path | None = None) -> tuple[str, str]:
    """Return (ric, working_field) for WTI. Fallback: (CLc1, TRDPRC_1)."""
    try:
        records = get_accessible_rics(group="wti_futures", role="primary", path=path)
        if records:
            return records[0]["ric"], records[0]["working_field"]
    except FileNotFoundError:
        pass
    return "CLc1", "TRDPRC_1"


def get_curve_rics(path: Path | None = None) -> list[dict[str, str]]:
    """Return accessible Brent curve RICs (role=curve)."""
    try:
        return get_accessible_rics(group="brent_futures", role="curve", path=path)
    except FileNotFoundError:
        logger.warning("No inventory — returning empty curve RIC list.")
        return []


def is_news_accessible(path: Path | None = None) -> bool:
    """Return True if LSEG news API was confirmed accessible in last discovery run."""
    try:
        df = load_inventory(path)
        row = df[df["ric"] == "_news_api"]
        return bool(row["accessible"].iloc[0]) if not row.empty else False
    except Exception:
        return False


def print_summary(df: pd.DataFrame) -> None:
    accessible = df[df["accessible"] & (df["ric"] != "_news_api")]
    total = len(df[df["ric"] != "_news_api"])
    print(f"\nDiscovery summary: {len(accessible)}/{total} instruments accessible.\n")
    print(df.to_string(index=False))
    news_row = df[df["ric"] == "_news_api"]
    if not news_row.empty:
        print(f"\nNews API: {'accessible' if news_row.iloc[0]['accessible'] else 'NOT accessible'}")


def run_discovery_and_save(
    start: str | None = None,
    end: str | None = None,
    probe_news: bool = True,
) -> pd.DataFrame:
    df = discover_instruments(start=start, end=end, probe_news=probe_news)
    print_summary(df)
    save_inventory(df)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    _start = sys.argv[1] if len(sys.argv) > 1 else None
    _end = sys.argv[2] if len(sys.argv) > 2 else None

    from src.session import managed_session

    with managed_session():
        run_discovery_and_save(start=_start, end=_end)
