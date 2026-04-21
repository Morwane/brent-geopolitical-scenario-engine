"""Event study and regime visualisation."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def plot_average_event_profile(
    profile: pd.DataFrame,
    title: str = "Average Cumulative Abnormal Return Around Events",
) -> go.Figure:
    """Mean CAR ± 1 std band across horizons."""
    if profile.empty:
        return go.Figure()
    x = profile.index.tolist()
    mean = profile["mean_car"]
    std  = profile["std_car"]
    fig = go.Figure()
    # Confidence band
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=(mean + std).tolist() + (mean - std).tolist()[::-1],
        fill="toself", fillcolor="rgba(31,119,180,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="± 1 std",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=mean, name="Mean CAR",
        line=dict(color="#1f77b4", width=2), mode="lines+markers",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="black", line_width=1)
    fig.update_layout(
        title=title, xaxis_title="Days after event",
        yaxis_title="CAR (log return)", template="plotly_white", height=370,
    )
    return fig


def plot_event_scatter(
    es_df: pd.DataFrame,
    ret_col: str = "brent_car_5d",
    colour_col: str = "direction",
    title: str | None = None,
) -> go.Figure:
    """Scatter of individual event outcomes, coloured by direction."""
    if es_df.empty or ret_col not in es_df.columns:
        return go.Figure()
    colour_map = {"escalation": "#d62728", "de-escalation": "#2ca02c", "neutral": "#7f7f7f"}
    fig = go.Figure()
    for direction, grp in es_df.groupby(colour_col):
        fig.add_trace(go.Scatter(
            x=grp["event_date"], y=grp[ret_col],
            mode="markers", name=str(direction),
            marker=dict(color=colour_map.get(str(direction), "#7f7f7f"), size=8, opacity=0.85),
            text=grp["label"],
            hovertemplate="%{text}<br>%{x|%Y-%m-%d}<br>CAR: %{y:.3f}<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="black", line_width=1)
    fig.update_layout(
        title=title or f"Event Reactions — {ret_col}",
        xaxis_title="Event Date", yaxis_title=ret_col,
        template="plotly_white", height=370,
    )
    return fig


def plot_regime_overlay(
    brent: pd.Series,
    regime_labels: pd.Series,
    title: str = "Brent Price with Regime Classification",
) -> go.Figure:
    """Price chart with shaded regime background bands."""
    colours = {
        "calm":               "rgba(44,160,44,0.08)",
        "controlled_tension": "rgba(255,127,14,0.10)",
        "escalation":         "rgba(214,39,40,0.12)",
    }
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=brent.index, y=brent,
        name="Brent", line=dict(color="#1f77b4", width=1.5),
    ))
    if not regime_labels.empty:
        current, start = None, None
        dates = regime_labels.index.tolist()
        for i, dt in enumerate(dates):
            r = str(regime_labels.iloc[i])
            if r != current:
                if current is not None and start is not None:
                    fig.add_vrect(
                        x0=str(start.date()), x1=str(dt.date()),
                        fillcolor=colours.get(current, "rgba(0,0,0,0.04)"),
                        layer="below", line_width=0,
                    )
                current, start = r, dt
        if current and start:
            fig.add_vrect(
                x0=str(start.date()), x1=str(dates[-1].date()),
                fillcolor=colours.get(current, "rgba(0,0,0,0.04)"),
                layer="below", line_width=0,
            )
    fig.update_layout(
        title=title, xaxis_title="Date", yaxis_title="USD/bbl",
        template="plotly_white", height=430,
    )
    return fig
