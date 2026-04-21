"""
Scenario engine.

Translates explicit geopolitical assumptions into Brent price and
calendar spread ranges under four scenarios:
  1. de_escalation
  2. persistent_tension
  3. severe_escalation
  4. escalation_with_opec_response

This is NOT a statistical forecasting model. It is an analytical framework.
Each scenario's economic logic is stated explicitly in scenarios.yaml
and reproduced in the output description. Parameters are transparent
and the outputs are ranges, not point estimates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
SCENARIOS_CONFIG_PATH = ROOT / "config" / "scenarios.yaml"
OUTPUTS_DIR = ROOT / "data" / "outputs"


def _load_scenarios() -> dict[str, Any]:
    with open(SCENARIOS_CONFIG_PATH) as f:
        return yaml.safe_load(f).get("scenarios", {})


def _baseline(
    prices: pd.Series,
    spread: pd.Series | None = None,
    window: int = 20,
) -> dict[str, float]:
    """Trailing-mean baseline from the most recent `window` trading days."""
    bl: dict[str, float] = {
        "brent_current": float(prices.dropna().iloc[-1]),
        "brent_baseline": float(prices.dropna().tail(window).mean()),
    }
    if spread is not None and not spread.empty:
        bl["spread_current"] = float(spread.dropna().iloc[-1])
        bl["spread_baseline"] = float(spread.dropna().tail(window).mean())
    else:
        bl["spread_current"] = float("nan")
        bl["spread_baseline"] = float("nan")
    return bl


def project_scenario(
    key: str,
    params: dict[str, Any],
    baseline: dict[str, float],
    n_paths: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate one scenario projection with a Monte Carlo endpoint distribution.

    The simulation samples uniformly within the scenario's return range
    and adds Gaussian noise scaled to 5% of the range width × vol multiplier.
    This produces a distribution of outcomes rather than a single point.
    """
    rng = np.random.default_rng(seed)
    brent = baseline["brent_current"]

    ret_lo, ret_hi = params["brent_return_range_pct"]
    spr_lo, spr_hi = params.get("m1_m3_spread_change_usd", [0.0, 0.0])
    bwti_lo, bwti_hi = params.get("brent_wti_change_usd", [0.0, 0.0])
    vol_mult = params.get("volatility_multiplier", 1.0)
    prob = params.get("probability_prior", float("nan"))

    brent_lo = brent * (1 + ret_lo / 100)
    brent_hi = brent * (1 + ret_hi / 100)

    centre = rng.uniform(brent_lo, brent_hi, n_paths)
    noise  = rng.normal(0, (brent_hi - brent_lo) * 0.05 * vol_mult, n_paths)
    sim_endpoints = centre + noise

    return {
        "scenario":           key,
        "label":              params.get("label", key),
        "description":        params.get("description", "").strip(),
        "probability_prior":  prob,
        "brent_current":      round(brent, 2),
        "brent_lo":           round(brent_lo, 2),
        "brent_central":      round((brent_lo + brent_hi) / 2, 2),
        "brent_hi":           round(brent_hi, 2),
        "spread_change_lo":   spr_lo,
        "spread_change_hi":   spr_hi,
        "brent_wti_lo":       bwti_lo,
        "brent_wti_hi":       bwti_hi,
        "vol_multiplier":     vol_mult,
        "sim_endpoints":      sim_endpoints,
    }


def run_all_scenarios(
    brent_prices: pd.Series,
    spread_m1_m3: pd.Series | None = None,
    n_paths: int = 2000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Run all four scenarios and return a list of result dicts."""
    config = _load_scenarios()
    bl = _baseline(brent_prices, spread_m1_m3)

    logger.info(
        "Scenario baseline: Brent=%.2f, M1-M3 spread=%.3f",
        bl["brent_current"], bl.get("spread_current", float("nan")),
    )

    return [
        project_scenario(key, params, bl, n_paths=n_paths, seed=seed + i)
        for i, (key, params) in enumerate(config.items())
    ]


def scenarios_to_table(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Format scenario results as a clean display table."""
    rows = []
    for r in results:
        prob = r["probability_prior"]
        prob_str = f"{prob:.0%}" if not np.isnan(prob) else "N/A"
        rows.append({
            "Scenario":          r["label"],
            "Prior Prob.":       prob_str,
            "Brent Low ($)":     r["brent_lo"],
            "Brent Central ($)": r["brent_central"],
            "Brent High ($)":    r["brent_hi"],
            "M1-M3 Chg Low":     r["spread_change_lo"],
            "M1-M3 Chg High":    r["spread_change_hi"],
            "Vol Multiplier":    r["vol_multiplier"],
        })
    return pd.DataFrame(rows)


def save_outputs(
    results: list[dict[str, Any]],
    output_dir: Path | None = None,
) -> None:
    """Save scenario summary table and per-scenario simulation distributions."""
    out = output_dir or OUTPUTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    table = scenarios_to_table(results)
    table.to_csv(out / "scenario_summary.csv", index=False)
    logger.info("Scenario summary saved → data/outputs/scenario_summary.csv")

    for r in results:
        key = r["scenario"]
        pd.Series(r["sim_endpoints"], name="brent_endpoint").to_csv(
            out / f"scenario_sim_{key}.csv", index=False
        )
