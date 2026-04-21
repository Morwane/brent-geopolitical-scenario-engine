"""Brent curve and calendar spread charts."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


_SPREAD_COLOURS = {
    "M1_M2": "#1f77b4", "M1_M3": "#ff7f0e",
    "M1_M6": "#2ca02c", "M6_M12": "#d62728",
    "brent_wti": "#9467bd",
}


def plot_calendar_spreads(
    spreads: pd.DataFrame,
    title: str = "Brent Calendar Spreads (USD/bbl)",
) -> go.Figure:
    fig = go.Figure()
    for col in spreads.columns:
        fig.add_trace(go.Scatter(
            x=spreads.index, y=spreads[col],
            name=col.replace("_", "-"),
            line=dict(color=_SPREAD_COLOURS.get(col, "#7f7f7f"), width=1.4),
        ))
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="black")
    fig.update_layout(
        title=title, xaxis_title="Date", yaxis_title="Spread (USD/bbl)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white", height=390,
    )
    return fig


def plot_curve_snapshot(
    curve: pd.DataFrame,
    dates: list[str] | None = None,
) -> go.Figure:
    """Snapshot of the Brent forward curve at selected dates.

    Parameters
    ----------
    curve : DataFrame with RIC columns (LCOc1 … LCOc12), date index
    dates : list of date strings to plot; defaults to latest available date
    """
    if curve.empty:
        return go.Figure()

    # Order columns by maturity month
    def _month(col: str) -> int:
        for p in ("LCOc", "CLc"):
            if col.startswith(p):
                try:
                    return int(col[len(p):])
                except ValueError:
                    pass
        return 99

    ordered = sorted([c for c in curve.columns if c.startswith("LCOc")], key=_month)
    if not ordered:
        ordered = list(curve.columns)

    plot_dates = dates or [str(curve.index.max().date())]
    fig = go.Figure()

    for d in plot_dates:
        try:
            row = curve.loc[pd.Timestamp(d), ordered].dropna()
        except KeyError:
            row = curve.iloc[-1][ordered].dropna()
        maturities = [_month(c) for c in row.index]
        fig.add_trace(go.Scatter(
            x=maturities, y=row.values,
            name=str(pd.Timestamp(d).date()),
            mode="lines+markers",
            line=dict(width=1.8),
        ))

    fig.update_layout(
        title="Brent Forward Curve Snapshot",
        xaxis_title="Months to delivery",
        yaxis_title="Price (USD/bbl)",
        template="plotly_white", height=380,
    )
    return fig


def plot_curve_structure_by_year(curve_metrics: pd.DataFrame) -> go.Figure:
    if "curve_structure" not in curve_metrics.columns:
        return go.Figure()
    df = curve_metrics[["curve_structure"]].copy()
    df.index = pd.to_datetime(df.index)
    df["year"] = df.index.year
    annual = df.groupby(["year", "curve_structure"]).size().unstack(fill_value=0)
    annual = (annual.div(annual.sum(axis=1), axis=0) * 100).round(1)
    fig = go.Figure()
    colours = {"backwardation": "#d62728", "contango": "#1f77b4"}
    for state in annual.columns:
        fig.add_trace(go.Bar(
            x=annual.index, y=annual[state],
            name=state.capitalize(),
            marker_color=colours.get(state, "#7f7f7f"),
        ))
    fig.update_layout(
        title="Brent Curve Structure by Year (% of Trading Days)",
        xaxis_title="Year", yaxis_title="%",
        barmode="stack", template="plotly_white", height=370,
    )
    return fig
