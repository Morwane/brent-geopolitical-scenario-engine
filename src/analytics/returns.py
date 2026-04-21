"""
Returns and volatility calculations. Pure functions — no I/O.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def log_returns(prices: pd.Series) -> pd.Series:
    return np.log(prices / prices.shift(1)).rename("log_return")


def pct_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().rename("pct_return")


def rolling_vol(
    returns: pd.Series,
    window: int = 21,
    annualise: bool = True,
    trading_days: int = 252,
) -> pd.Series:
    vol = returns.rolling(window).std()
    if annualise:
        vol = vol * np.sqrt(trading_days)
    return vol.rename(f"vol_{window}d")


def ewm_vol(
    returns: pd.Series,
    halflife: int = 10,
    annualise: bool = True,
    trading_days: int = 252,
) -> pd.Series:
    vol = returns.ewm(halflife=halflife).std()
    if annualise:
        vol = vol * np.sqrt(trading_days)
    return vol.rename(f"ewm_vol_hl{halflife}")


def compute_return_features(prices: pd.Series) -> pd.DataFrame:
    """Build a standard feature set: log_return, pct_return, vol_5d, vol_21d, vol_63d."""
    lr = log_returns(prices)
    return pd.DataFrame({
        "log_return": lr,
        "pct_return": pct_returns(prices),
        "vol_5d":  rolling_vol(lr, 5),
        "vol_21d": rolling_vol(lr, 21),
        "vol_63d": rolling_vol(lr, 63),
    })
