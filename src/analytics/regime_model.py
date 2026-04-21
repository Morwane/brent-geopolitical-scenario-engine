"""
Market regime detection.

Classifies each trading day into:
  0 = calm
  1 = controlled tension
  2 = escalation

Primary method: Gaussian Hidden Markov Model (hmmlearn).
HMM is appropriate here because geopolitical regimes persist over time
and transition — they are not i.i.d. cluster assignments.

Fallback: volatility percentile + geo_shock_score threshold classifier,
used when hmmlearn is unavailable.

Features: Brent log return, 5-day realised vol, M1-M3 spread (if available),
geo_shock_score (if available).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

REGIME_LABELS: dict[int, str] = {0: "calm", 1: "controlled_tension", 2: "escalation"}
N_STATES = 3


def _build_feature_matrix(
    log_return: pd.Series,
    vol_5d: pd.Series,
    spread_m1_m3: pd.Series | None = None,
    geo_shock: pd.Series | None = None,
) -> pd.DataFrame:
    cols: dict[str, pd.Series] = {"log_return": log_return, "vol_5d": vol_5d}
    if spread_m1_m3 is not None and not spread_m1_m3.empty:
        cols["m1_m3_spread"] = spread_m1_m3
    if geo_shock is not None and not geo_shock.empty:
        cols["geo_shock_score"] = geo_shock
    return pd.DataFrame(cols).dropna()


def fit_hmm(
    features: pd.DataFrame,
    n_states: int = N_STATES,
    n_iter: int = 200,
    random_state: int = 42,
) -> tuple[object, StandardScaler]:
    """Fit a Gaussian HMM. Returns (model, fitted_scaler)."""
    try:
        from hmmlearn import hmm  # type: ignore
    except ImportError:
        raise ImportError("hmmlearn required: pip install hmmlearn")

    scaler = StandardScaler()
    X = scaler.fit_transform(features.values)

    model = hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=n_iter,
        random_state=random_state,
        verbose=False,
    )
    model.fit(X)
    logger.info("HMM fit complete. Converged: %s", model.monitor_.converged)
    return model, scaler


def _order_by_volatility(
    features: pd.DataFrame, raw_states: pd.Series
) -> dict[int, int]:
    """Map raw state IDs → ordered IDs where 0=lowest vol, 2=highest vol."""
    vol_col = "vol_5d" if "vol_5d" in features.columns else features.columns[1]
    mean_vols = {
        int(s): float(features.loc[raw_states == s, vol_col].mean())
        for s in raw_states.unique()
    }
    return {raw: ordered for ordered, raw in enumerate(sorted(mean_vols, key=mean_vols.get))}


def predict_regimes(
    model: object,
    scaler: StandardScaler,
    features: pd.DataFrame,
) -> pd.Series:
    """Decode state sequence from fitted HMM. Returns integer Series indexed by date."""
    X = scaler.transform(features.values)
    return pd.Series(model.predict(X), index=features.index, name="regime_raw")  # type: ignore[attr-defined]


def fallback_threshold_classifier(
    vol_5d: pd.Series,
    geo_shock: pd.Series | None = None,
    calm_pct: float = 0.40,
    tension_pct: float = 0.75,
) -> pd.Series:
    """Deterministic regime classifier based on volatility percentiles.

    Optionally upgrades regime by one level on high geo-stress days.
    """
    q_calm = vol_5d.quantile(calm_pct)
    q_tension = vol_5d.quantile(tension_pct)

    def _classify(v: float) -> int:
        if v <= q_calm:
            return 0
        if v <= q_tension:
            return 1
        return 2

    regime = vol_5d.apply(_classify).rename("regime")

    if geo_shock is not None:
        high_geo = (geo_shock > geo_shock.quantile(0.85)).reindex(regime.index).fillna(False)
        regime = regime.where(~high_geo, other=(regime + 1).clip(upper=2))

    return regime


def fit_and_predict(
    log_return: pd.Series,
    vol_5d: pd.Series,
    spread_m1_m3: pd.Series | None = None,
    geo_shock: pd.Series | None = None,
    use_hmm: bool = True,
    n_states: int = N_STATES,
) -> pd.DataFrame:
    """End-to-end regime detection: feature prep → model → labelled output.

    Returns DataFrame with: regime (int), regime_label (str), + feature columns.
    """
    features = _build_feature_matrix(log_return, vol_5d, spread_m1_m3, geo_shock)
    if features.empty:
        logger.warning("No valid feature rows — returning empty DataFrame.")
        return pd.DataFrame()

    try:
        if not use_hmm:
            raise ImportError("use_hmm=False")
        model, scaler = fit_hmm(features, n_states=n_states)
        raw = predict_regimes(model, scaler, features)
        mapping = _order_by_volatility(features, raw)
        regimes = raw.map(mapping).rename("regime")
    except ImportError:
        logger.warning("HMM unavailable — using threshold classifier.")
        vol = features.get("vol_5d", features.iloc[:, 1])
        geo  = features.get("geo_shock_score", None)
        regimes = fallback_threshold_classifier(vol, geo)

    result = features.copy()
    result["regime"] = regimes
    result["regime_label"] = regimes.map(REGIME_LABELS)
    return result


def regime_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive statistics per regime."""
    if "regime_label" not in df.columns:
        return pd.DataFrame()
    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != "regime"]
    return df.groupby("regime_label")[num_cols].agg(["mean", "std"]).round(4)
