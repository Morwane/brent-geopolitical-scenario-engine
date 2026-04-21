"""Tests for src/analytics/event_study.py — no LSEG session required."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.event_study import (
    Event,
    EventStudyConfig,
    average_event_profile,
    run_event_study,
    run_multi_series_event_study,
    summary_by_direction,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_returns() -> pd.Series:
    rng = np.random.default_rng(42)
    idx = pd.date_range("2023-01-03", periods=260, freq="B")
    return pd.Series(rng.normal(0, 0.015, 260), index=idx, name="brent_log_return")


@pytest.fixture()
def sample_events() -> list[Event]:
    return [
        Event(date=pd.Timestamp("2023-03-15"), label="Strike A", direction="escalation"),
        Event(date=pd.Timestamp("2023-06-01"), label="Ceasefire B", direction="de-escalation"),
        Event(date=pd.Timestamp("2023-09-20"), label="Talks C", direction="de-escalation"),
    ]


# ── run_event_study ───────────────────────────────────────────────────────────

def test_event_study_returns_one_row_per_event(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events)
    assert len(df) == len(sample_events)


def test_event_study_has_car_columns(sample_returns, sample_events):
    cfg = EventStudyConfig(post_event_windows=[1, 3, 5])
    df = run_event_study(sample_returns, sample_events, config=cfg)
    for h in [1, 3, 5]:
        assert f"brent_car_{h}d" in df.columns


def test_event_study_meta_columns(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events)
    assert "event_date" in df.columns
    assert "label" in df.columns
    assert "direction" in df.columns


def test_event_study_custom_label(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events, series_label="test_series")
    assert "test_series_car_1d" in df.columns


def test_event_study_no_events(sample_returns):
    df = run_event_study(sample_returns, [])
    assert len(df) == 0


# ── run_multi_series_event_study ──────────────────────────────────────────────

def test_multi_series_merges_columns(sample_returns, sample_events):
    spread_rets = sample_returns * 0.3
    result = run_multi_series_event_study(
        {"brent": sample_returns, "M1_M3": spread_rets},
        sample_events,
    )
    assert "brent_car_1d" in result.columns
    assert "M1_M3_car_1d" in result.columns
    assert len(result) == len(sample_events)


# ── summary_by_direction ──────────────────────────────────────────────────────

def test_summary_by_direction_groups(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events)
    summary = summary_by_direction(df, "brent_car_5d")
    assert "escalation" in summary.index
    assert "de-escalation" in summary.index


def test_summary_by_direction_columns(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events)
    summary = summary_by_direction(df, "brent_car_5d")
    assert "n_events" in summary.columns
    assert "mean_car" in summary.columns
    assert "p_value" in summary.columns


# ── average_event_profile ─────────────────────────────────────────────────────

def test_average_event_profile_index(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events)
    profile = average_event_profile(df, horizons=[1, 3, 5])
    assert set(profile.index) == {1, 3, 5}


def test_average_event_profile_direction_filter(sample_returns, sample_events):
    df = run_event_study(sample_returns, sample_events)
    profile_esc = average_event_profile(df, direction_filter="escalation")
    assert len(profile_esc) > 0
