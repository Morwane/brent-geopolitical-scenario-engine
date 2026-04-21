"""Brent and WTI price history charts."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_price_history(
    prices: pd.DataFrame,
    event_dates: list[dict] | None = None,
    title: str = "Brent and WTI — Daily Price (USD/bbl)",
) -> go.Figure:
    """Line chart with optional geopolitical event overlays.

    event_dates: list of dicts with keys: date, label, direction
                 direction='escalation' → red, 'de-escalation' → green
    """
    fig = go.Figure()

    if "brent" in prices.columns:
        fig.add_trace(go.Scatter(
            x=prices.index, y=prices["brent"],
            name="Brent (LCOc1)", line=dict(color="#1f77b4", width=1.6),
        ))
    if "wti" in prices.columns:
        fig.add_trace(go.Scatter(
            x=prices.index, y=prices["wti"],
            name="WTI (CLc1)", line=dict(color="#ff7f0e", width=1.3, dash="dot"),
        ))

    for ev in (event_dates or []):
        dt = pd.Timestamp(ev["date"])
        colour = "#d62728" if ev.get("direction") == "escalation" else "#2ca02c"
        fig.add_shape(
            type="line",
            xref="x", yref="paper",
            x0=dt, x1=dt,
            y0=0, y1=1,
            line=dict(color=colour, width=1, dash="dash"),
        )
        fig.add_annotation(
            x=dt,
            yref="paper", y=1.0,
            text=str(ev.get("label", "")),
            showarrow=False,
            yshift=10,
            font=dict(size=9, color=colour),
            textangle=-90,
        )

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="USD / bbl",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=440,
    )
    return fig


def plot_price_with_vol(
    prices: pd.DataFrame,
    vol: pd.Series,
) -> go.Figure:
    """Two-panel: Brent price (top) + rolling vol (bottom)."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.65, 0.35], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=prices.index, y=prices.get("brent", pd.Series()),
                             name="Brent", line=dict(color="#1f77b4", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=vol.index, y=vol, name="21d Vol (ann.)",
                             line=dict(color="#9467bd", width=1.2),
                             fill="tozeroy", fillcolor="rgba(148,103,189,0.15)"), row=2, col=1)
    fig.update_layout(
        title="Brent Price and 21-Day Realised Volatility",
        yaxis_title="USD/bbl", yaxis2_title="Ann. Vol",
        template="plotly_white", height=490,
    )
    return fig
