"""Tests for src/analytics/spreads.py — pure functions, no LSEG session needed."""

import pandas as pd
import pytest

from src.analytics.spreads import (
    SPREAD_DEFINITIONS,
    brent_wti_spread,
    calendar_spread,
    compute_all_calendar_spreads,
    spread_summary_stats,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_curve() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=10, freq="B")
    return pd.DataFrame({
        "LCOc1":  [80.0 + i * 0.1 for i in range(10)],
        "LCOc2":  [78.0 + i * 0.1 for i in range(10)],
        "LCOc3":  [76.0 + i * 0.1 for i in range(10)],
        "LCOc6":  [73.0 + i * 0.1 for i in range(10)],
        "LCOc12": [70.0 + i * 0.1 for i in range(10)],
    }, index=idx)


@pytest.fixture()
def sample_prices() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=10, freq="B")
    return pd.DataFrame({
        "brent": [80.0 + i * 0.1 for i in range(10)],
        "wti":   [77.0 + i * 0.1 for i in range(10)],
    }, index=idx)


# ── calendar_spread ───────────────────────────────────────────────────────────

def test_calendar_spread_backwardation(sample_curve):
    s = calendar_spread(sample_curve, "LCOc1", "LCOc2")
    assert (s > 0).all(), "LCOc1 > LCOc2 → should be backwardation (positive)"


def test_calendar_spread_length(sample_curve):
    s = calendar_spread(sample_curve, "LCOc1", "LCOc3")
    assert len(s) == 10


def test_calendar_spread_missing_column(sample_curve):
    with pytest.raises(KeyError):
        calendar_spread(sample_curve, "LCOc1", "LCOc99")


def test_calendar_spread_label(sample_curve):
    s = calendar_spread(sample_curve, "LCOc1", "LCOc2", label="M1M2_test")
    assert s.name == "M1M2_test"


# ── compute_all_calendar_spreads ──────────────────────────────────────────────

def test_all_spreads_columns(sample_curve):
    df = compute_all_calendar_spreads(sample_curve)
    expected = set(SPREAD_DEFINITIONS.keys())
    assert expected.issubset(set(df.columns))


def test_all_spreads_skip_missing():
    # DataFrame with only M1 and M2 — M1_M3, M1_M6, M6_M12 should be skipped
    idx = pd.date_range("2024-01-02", periods=5, freq="B")
    partial = pd.DataFrame({"LCOc1": [80.0] * 5, "LCOc2": [78.0] * 5}, index=idx)
    df = compute_all_calendar_spreads(partial, skip_missing=True)
    assert "M1_M2" in df.columns
    assert "M1_M3" not in df.columns


def test_all_spreads_no_skip_raises():
    idx = pd.date_range("2024-01-02", periods=5, freq="B")
    partial = pd.DataFrame({"LCOc1": [80.0] * 5}, index=idx)
    with pytest.raises(KeyError):
        compute_all_calendar_spreads(partial, skip_missing=False)


# ── brent_wti_spread ─────────────────────────────────────────────────────────

def test_brent_wti_positive(sample_prices):
    s = brent_wti_spread(sample_prices)
    assert (s > 0).all()


def test_brent_wti_name(sample_prices):
    s = brent_wti_spread(sample_prices)
    assert s.name == "brent_wti"


def test_brent_wti_missing_column():
    df = pd.DataFrame({"brent": [80.0]})
    with pytest.raises(KeyError):
        brent_wti_spread(df)


# ── spread_summary_stats ──────────────────────────────────────────────────────

def test_spread_summary_stats(sample_curve):
    spreads = compute_all_calendar_spreads(sample_curve)
    stats = spread_summary_stats(spreads)
    assert set(stats.columns) == {"mean", "std", "min", "p25", "p50", "p75", "max", "pct_backwardation"}
    assert (stats["pct_backwardation"] >= 0).all()
    assert (stats["pct_backwardation"] <= 1).all()
