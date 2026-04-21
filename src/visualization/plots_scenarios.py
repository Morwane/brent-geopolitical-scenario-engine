"""Scenario and fan chart visualisation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.analytics.probabilistic_projection import fan_chart_quantiles

_SCENARIO_COLOURS = {
    "de_escalation":              "#2ca02c",
    "persistent_tension":         "#ff7f0e",
    "severe_escalation":          "#d62728",
    "escalation_with_opec_response": "#9467bd",
}


def plot_scenario_ranges(
    results: list[dict[str, Any]],
    title: str = "Brent Scenario Range Projections",
) -> go.Figure:
    """Horizontal bar chart showing Brent low / central / high for each scenario."""
    fig = go.Figure()

    scenarios = [r["label"] for r in results]
    lows      = [r["brent_lo"] for r in results]
    centrals  = [r["brent_central"] for r in results]
    highs     = [r["brent_hi"] for r in results]

    # Range bars (low to high)
    for i, r in enumerate(results):
        colour = _SCENARIO_COLOURS.get(r["scenario"], "#7f7f7f")
        fig.add_trace(go.Bar(
            x=[r["brent_hi"] - r["brent_lo"]],
            y=[r["label"]],
            base=[r["brent_lo"]],
            orientation="h",
            name=r["label"],
            marker_color=colour,
            opacity=0.55,
            showlegend=True,
        ))
        # Central marker
        fig.add_trace(go.Scatter(
            x=[r["brent_central"]], y=[r["label"]],
            mode="markers",
            marker=dict(color=colour, size=10, symbol="diamond"),
            showlegend=False,
        ))

    # Current price reference
    current = results[0]["brent_current"] if results else None
    if current:
        fig.add_vline(
            x=current, line_dash="dash", line_color="black", line_width=1.5,
            annotation_text=f"Current: ${current:.1f}",
            annotation_position="top right",
        )

    fig.update_layout(
        title=title,
        xaxis_title="Brent Price (USD/bbl)",
        yaxis_title="Scenario",
        barmode="overlay",
        template="plotly_white",
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_fan_chart(
    results: list[dict[str, Any]],
    current_price: float | None = None,
    title: str = "Probability-Weighted Brent Fan Chart",
) -> go.Figure:
    """Fan chart from probability-weighted blended scenario distributions."""
    quantiles_dict = fan_chart_quantiles(results)
    if not quantiles_dict:
        return go.Figure()

    fig = go.Figure()

    # Outer band: p5 – p95
    fig.add_trace(go.Bar(
        x=["Blended Distribution"],
        y=[quantiles_dict.get("p95", 0) - quantiles_dict.get("p5", 0)],
        base=[quantiles_dict.get("p5", 0)],
        name="p5–p95",
        marker_color="rgba(31,119,180,0.15)",
        width=0.3,
        showlegend=True,
    ))
    # Inner band: p25 – p75
    fig.add_trace(go.Bar(
        x=["Blended Distribution"],
        y=[quantiles_dict.get("p75", 0) - quantiles_dict.get("p25", 0)],
        base=[quantiles_dict.get("p25", 0)],
        name="p25–p75",
        marker_color="rgba(31,119,180,0.40)",
        width=0.3,
        showlegend=True,
    ))
    # Median
    fig.add_shape(
        type="line",
        x0=-0.2, x1=0.2,
        y0=quantiles_dict.get("p50", 0), y1=quantiles_dict.get("p50", 0),
        line=dict(color="#1f77b4", width=2.5),
    )

    if current_price:
        fig.add_hline(
            y=current_price, line_dash="dash", line_color="black",
            annotation_text=f"Current: ${current_price:.1f}",
        )

    fig.update_layout(
        title=title, yaxis_title="Brent (USD/bbl)",
        barmode="overlay", template="plotly_white", height=380,
    )
    return fig


def plot_scenario_distributions(
    results: list[dict[str, Any]],
    title: str = "Scenario Simulated Brent Endpoint Distributions",
) -> go.Figure:
    """Overlapping histogram of simulated endpoints per scenario."""
    fig = go.Figure()
    for r in results:
        eps = r.get("sim_endpoints")
        if eps is None or len(eps) == 0:
            continue
        colour = _SCENARIO_COLOURS.get(r["scenario"], "#7f7f7f")
        fig.add_trace(go.Histogram(
            x=eps, name=r["label"],
            nbinsx=60,
            marker_color=colour,
            opacity=0.50,
        ))
    fig.update_layout(
        title=title, barmode="overlay",
        xaxis_title="Brent (USD/bbl)", yaxis_title="Count",
        template="plotly_white", height=380,
    )
    return fig
