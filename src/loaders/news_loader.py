"""
Geopolitical news loader.

Confirmed accessible (discovery 2026-04-21):
  ld.news.get_headlines() — working
  Column schema: headline, storyId, sourceCode, versionCreated (index or column)

Fetches LSEG headlines for Iran / Hormuz / sanctions / OPEC+ topics.
Falls back to data/raw/manual_events.csv if the news API is unavailable
or returns insufficient data.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
FIELDS_CONFIG_PATH = ROOT / "config" / "fields.yaml"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

MANUAL_EVENTS_PATH = RAW_DIR / "manual_events.csv"
NEWS_OUTPUT_PATH = PROCESSED_DIR / "news_headlines.csv"


def _news_topics() -> list[str]:
    try:
        with open(FIELDS_CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        return cfg.get("news", {}).get("geopolitical_topics", [])
    except Exception:
        return ["Iran", "Strait of Hormuz", "sanctions", "OPEC", "escalation"]


def _fetch_topic(query: str, start: str, end: str, max_count: int = 200) -> pd.DataFrame:
    """Fetch headlines for one query string from ld.news.get_headlines."""
    try:
        import lseg.data as ld  # type: ignore

        results = ld.news.get_headlines(
            query=query,
            start=start,
            end=end,
            count=max_count,
        )
        return results if (results is not None and not results.empty) else pd.DataFrame()
    except Exception as exc:
        logger.debug("News fetch failed for '%s': %s", query, exc)
        return pd.DataFrame()


def _standardise(df: pd.DataFrame, query_term: str) -> pd.DataFrame:
    """Normalise raw LSEG news output to: date, headline, source, query_term.

    LSEG news schema (confirmed 2026-04-21):
      index or column: versionCreated (datetime with tz)
      headline        : headline text
      storyId         : story identifier
      sourceCode      : e.g. NS:RTRS
    """
    out = pd.DataFrame()

    # Date — may be index or column
    if "versionCreated" in df.columns:
        out["date"] = pd.to_datetime(df["versionCreated"], utc=True)
    elif df.index.name == "versionCreated" or pd.api.types.is_datetime64_any_dtype(df.index):
        out["date"] = pd.to_datetime(df.index, utc=True)
    else:
        out["date"] = pd.NaT

    out["date"] = out["date"].dt.tz_convert(None).dt.normalize()

    # Headline text — confirmed column name is "headline"
    for col in ["headline", "text", "headlineText", "Headline"]:
        if col in df.columns:
            out["headline"] = df[col].astype(str).values
            break
    if "headline" not in out.columns:
        out["headline"] = ""

    # Source
    for col in ["sourceCode", "source", "Source"]:
        if col in df.columns:
            out["source"] = df[col].astype(str).values
            break
    if "source" not in out.columns:
        out["source"] = ""

    out["query_term"] = query_term
    return out.dropna(subset=["date"]).reset_index(drop=True)


def fetch_news(
    start: str,
    end: str,
    save: bool = True,
) -> pd.DataFrame:
    """Fetch and combine geopolitical headlines for all configured topics.

    Falls back to manual_events.csv if the API returns nothing.

    Parameters
    ----------
    start, end : YYYY-MM-DD
    save       : write combined output to data/processed/news_headlines.csv

    Returns
    -------
    pd.DataFrame — columns: date, headline, source, query_term
    """
    topics = _news_topics()
    frames: list[pd.DataFrame] = []

    for topic in topics:
        logger.info("Fetching news: '%s'", topic)
        raw = _fetch_topic(topic, start, end)
        if raw.empty:
            logger.info("  -> 0 results")
            continue
        clean = _standardise(raw, topic)
        logger.info("  -> %d headlines", len(clean))
        frames.append(clean)

    if not frames:
        logger.warning(
            "News API returned no results for any topic. "
            "Falling back to manual_events.csv."
        )
        return _load_fallback()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["date", "headline"]).sort_values("date")
    logger.info("Total unique headlines: %d", len(combined))

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        combined.to_csv(NEWS_OUTPUT_PATH, index=False)
        logger.info("Saved → data/processed/news_headlines.csv")

    return combined


def load_news_from_file() -> pd.DataFrame:
    """Load previously saved headlines."""
    if NEWS_OUTPUT_PATH.exists():
        return pd.read_csv(NEWS_OUTPUT_PATH, parse_dates=["date"])
    logger.warning("No saved news file — returning empty frame.")
    return _empty()


def _load_fallback() -> pd.DataFrame:
    """Load manual_events.csv as fallback; create empty template if missing."""
    if MANUAL_EVENTS_PATH.exists():
        df = pd.read_csv(MANUAL_EVENTS_PATH, parse_dates=["date"])
        logger.info("Loaded %d manual events from %s", len(df), MANUAL_EVENTS_PATH)
        return df
    _create_manual_events_template()
    return _empty()


def _create_manual_events_template() -> None:
    """Create an empty CSV template at data/raw/manual_events.csv."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cols = ["date", "label", "category", "description", "direction"]
    pd.DataFrame(columns=cols).to_csv(MANUAL_EVENTS_PATH, index=False)
    print(f"\n[ACTION REQUIRED] Populate your event list at: {MANUAL_EVENTS_PATH}")
    print("  direction values: escalation | de-escalation | neutral\n")


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "headline", "source", "query_term"])
