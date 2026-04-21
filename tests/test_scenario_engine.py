"""Tests for src/analytics/scenario_engine.py — no LSEG session required."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.scenario_engine import (
    _baseline,
    project_scenario,
    run_all_scenarios,
    scenarios_to_table,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_prices() -> pd.Series:
    idx = pd.date_range("2023-01-03", periods=100, freq="B")
    prices = 80.0 + np.cumsum(np.random.default_rng(42).normal(0, 0.5, 100))
    return pd.Series(prices, index=idx, name="brent")


@pytest.fixture()
def sample_spread() -> pd.Series:
    idx = pd.date_range("2023-01-03", periods=100, freq="B")
    return pd.Series(
        2.0 + np.random.default_rng(42).normal(0, 0.3, 100), index=idx, name="M1_M3"
    )


@pytest.fixture()
def dummy_scenario_params() -> dict:
    return {
        "label": "Test Scenario",
        "description": "Test",
        "probability_prior": 0.25,
        "brent_return_range_pct": [-10, 0],
        "m1_m3_spread_change_usd": [-1.0, 0.0],
        "brent_wti_change_usd": [-0.5, 0.0],
        "volatility_multiplier": 1.0,
    }


# ── _baseline ─────────────────────────────────────────────────────────────────

def test_baseline_keys(sample_prices):
    bl = _baseline(sample_prices)
    assert "brent_current" in bl
    assert "brent_baseline" in bl


def test_baseline_current_equals_last(sample_prices):
    bl = _baseline(sample_prices)
    assert bl["brent_current"] == pytest.approx(float(sample_prices.dropna().iloc[-1]))


def test_baseline_with_spread(sample_prices, sample_spread):
    bl = _baseline(sample_prices, sample_spread)
    assert "spread_current" in bl
    assert not np.isnan(bl["spread_current"])


# ── project_scenario ──────────────────────────────────────────────────────────

def test_project_scenario_keys(sample_prices, dummy_scenario_params):
    bl = _baseline(sample_prices)
    result = project_scenario("test", dummy_scenario_params, bl)
    for key in ("scenario", "label", "brent_lo", "brent_central", "brent_hi", "sim_endpoints"):
        assert key in result


def test_project_scenario_range_ordering(sample_prices, dummy_scenario_params):
    bl = _baseline(sample_prices)
    result = project_scenario("test", dummy_scenario_params, bl)
    assert result["brent_lo"] <= result["brent_central"] <= result["brent_hi"]


def test_project_scenario_sim_length(sample_prices, dummy_scenario_params):
    bl = _baseline(sample_prices)
    result = project_scenario("test", dummy_scenario_params, bl, n_paths=500)
    assert len(result["sim_endpoints"]) == 500


def test_project_scenario_endpoints_near_range(sample_prices, dummy_scenario_params):
    bl = _baseline(sample_prices)
    result = project_scenario("test", dummy_scenario_params, bl, n_paths=1000)
    median_sim = float(np.median(result["sim_endpoints"]))
    # Median should be near the central value (within 10% of current price)
    assert abs(median_sim - result["brent_central"]) < result["brent_current"] * 0.10


# ── run_all_scenarios ─────────────────────────────────────────────────────────

def test_run_all_scenarios_count(sample_prices):
    results = run_all_scenarios(sample_prices)
    assert len(results) == 4  # 4 scenarios in scenarios.yaml


def test_run_all_scenarios_labels(sample_prices):
    results = run_all_scenarios(sample_prices)
    labels = {r["scenario"] for r in results}
    expected = {
        "de_escalation", "persistent_tension",
        "severe_escalation", "escalation_with_opec_response",
    }
    assert labels == expected


def test_run_all_scenarios_prior_sum(sample_prices):
    results = run_all_scenarios(sample_prices)
    total = sum(r["probability_prior"] for r in results)
    assert abs(total - 1.0) < 1e-6


# ── scenarios_to_table ────────────────────────────────────────────────────────

def test_scenarios_to_table_shape(sample_prices):
    results = run_all_scenarios(sample_prices)
    table = scenarios_to_table(results)
    assert len(table) == 4
    assert "Brent Low ($)" in table.columns
    assert "Brent High ($)" in table.columns
