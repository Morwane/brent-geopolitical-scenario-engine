"""
Probabilistic projection helpers.

Builds probability-weighted blended distributions and quantile outputs
from scenario simulation results. Used for fan charts and output tables.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def scenario_quantile_table(
    results: list[dict[str, Any]],
    quantiles: list[float] | None = None,
) -> pd.DataFrame:
    """Quantile table for each scenario's simulated endpoint distribution.

    Returns DataFrame: rows = scenarios, columns = p5 … p95.
    """
    quantiles = quantiles or QUANTILES
    rows = []
    for r in results:
        endpoints = r.get("sim_endpoints")
        if endpoints is None or len(endpoints) == 0:
            continue
        q_vals = np.quantile(endpoints, quantiles)
        row = {"scenario": r["label"]}
        for q, v in zip(quantiles, q_vals):
            row[f"p{int(q * 100)}"] = round(v, 2)
        rows.append(row)
    return pd.DataFrame(rows).set_index("scenario")


def probability_weighted_distribution(
    results: list[dict[str, Any]],
    n_samples: int = 5000,
    seed: int = 99,
) -> np.ndarray:
    """Draw a probability-weighted sample from all scenario distributions.

    Scenarios without a prior receive equal weight.
    Returns a 1-D array of length n_samples.
    """
    rng = np.random.default_rng(seed)
    priors = [r.get("probability_prior", float("nan")) for r in results]
    priors = [p if not np.isnan(p) else 0.0 for p in priors]
    total = sum(priors)
    weights = [p / total for p in priors] if total > 0 else [1 / len(results)] * len(results)

    counts = [int(round(w * n_samples)) for w in weights]
    counts[-1] = n_samples - sum(counts[:-1])

    blended: list[np.ndarray] = []
    for r, count in zip(results, counts):
        eps = r.get("sim_endpoints")
        if eps is None or count <= 0:
            continue
        blended.append(rng.choice(eps, size=count, replace=True))

    return np.concatenate(blended) if blended else np.array([])


def fan_chart_quantiles(
    results: list[dict[str, Any]],
    quantiles: list[float] | None = None,
) -> dict[str, float]:
    """Compute quantile values from the blended distribution for a fan chart.

    Returns dict: {"p5": ..., "p25": ..., "p50": ..., "p75": ..., "p95": ...}.
    """
    quantiles = quantiles or QUANTILES
    blended = probability_weighted_distribution(results)
    if len(blended) == 0:
        return {}
    q_vals = np.quantile(blended, quantiles)
    return {f"p{int(q * 100)}": round(v, 2) for q, v in zip(quantiles, q_vals)}
