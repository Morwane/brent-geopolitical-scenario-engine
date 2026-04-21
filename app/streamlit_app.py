"""
Brent Geopolitical Scenario Engine — Streamlit Dashboard.

Run with:
    streamlit run app/streamlit_app.py

Loads cached data from data/processed/ by default.
A live LSEG session is only needed to refresh data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.curve_metrics import compute_curve_metrics, summarise_curve_regimes
from src.analytics.returns import compute_return_features
from src.analytics.scenario_engine import run_all_scenarios, scenarios_to_table
from src.analytics.spreads import build_spread_panel, spread_summary_stats
from src.visualization.plots_curve import (
    plot_calendar_spreads,
    plot_curve_snapshot,
    plot_curve_structure_by_year,
)
from src.visualization.plots_event import plot_event_scatter, plot_regime_overlay
from src.visualization.plots_price import plot_price_history, plot_price_with_vol
from src.visualization.plots_scenarios import (
    plot_fan_chart,
    plot_scenario_distributions,
    plot_scenario_ranges,
)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Brent Geopolitical Scenario Engine",
    page_icon="🛢️",
    layout="wide",
)

st.title("🛢️ Brent Under Geopolitical Stress")
st.caption(
    "Event-Driven Forecasting and Scenario Engine — LSEG Pricing and News Data"
)

# ── Data loading helpers ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _load_prices() -> pd.DataFrame:
    try:
        from src.loaders.prices_loader import load_prices_from_file
        return load_prices_from_file()
    except FileNotFoundError:
        st.warning(
            "No cached prices found. Run `python -m src.loaders.prices_loader` "
            "with an active LSEG session to populate data."
        )
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def _load_curve() -> pd.DataFrame:
    try:
        from src.loaders.futures_loader import load_curve_from_file
        return load_curve_from_file()
    except FileNotFoundError:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def _load_events() -> pd.DataFrame:
    path = ROOT / "data" / "raw" / "manual_events.csv"
    if path.exists():
        return pd.read_csv(path, parse_dates=["date"])
    return pd.DataFrame(columns=["date", "label", "direction"])


@st.cache_data(ttl=3600)
def _load_news() -> pd.DataFrame:
    path = ROOT / "data" / "processed" / "news_headlines.csv"
    if path.exists():
        return pd.read_csv(path, parse_dates=["date"])
    return pd.DataFrame(columns=["date", "headline", "source"])


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Controls")
    refresh_data = st.button("🔄 Refresh Data from LSEG", help="Opens a live session to reload all data.")
    st.markdown("---")
    st.subheader("Date Range Filter")
    prices_raw = _load_prices()
    if not prices_raw.empty:
        min_date = prices_raw.index.min().date()
        max_date = prices_raw.index.max().date()
    else:
        from datetime import date, timedelta
        min_date = date(2020, 1, 1)
        max_date = date.today()

    date_start = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date)
    date_end   = st.date_input("To",   value=max_date, min_value=min_date, max_value=max_date)
    st.markdown("---")
    show_wti = st.checkbox("Show WTI", value=True)

# ── Data refresh ──────────────────────────────────────────────────────────────

if refresh_data:
    with st.spinner("Opening LSEG session and refreshing data..."):
        try:
            from src.session import managed_session
            from src.loaders.prices_loader import load_prices
            from src.loaders.futures_loader import load_curve
            with managed_session():
                load_prices(str(date_start), str(date_end), save=True)
                load_curve(str(date_start), str(date_end), save=True)
            st.cache_data.clear()
            st.success("Data refreshed.")
        except Exception as e:
            st.error(f"LSEG refresh failed: {e}")

# ── Load and filter ───────────────────────────────────────────────────────────

prices = _load_prices()
curve  = _load_curve()
events_df = _load_events()
news_df   = _load_news()

if not prices.empty:
    prices = prices.loc[str(date_start) : str(date_end)]
if not curve.empty:
    curve  = curve.loc[str(date_start) : str(date_end)]

if not show_wti and "wti" in prices.columns:
    prices = prices.drop(columns=["wti"])

event_list = []
if not events_df.empty:
    for _, row in events_df.iterrows():
        event_list.append({
            "date": row["date"],
            "label": row.get("label", ""),
            "direction": row.get("direction", ""),
        })

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_price, tab_curve, tab_events, tab_regime, tab_scenarios = st.tabs([
    "📈 Price History",
    "📊 Curve & Spreads",
    "📰 Event Study",
    "🎯 Regime",
    "🔭 Scenarios",
])

# ─── Tab 1: Price History ─────────────────────────────────────────────────────
with tab_price:
    if prices.empty:
        st.info("No price data loaded. Use the sidebar to refresh from LSEG.")
    else:
        st.plotly_chart(
            plot_price_history(prices, event_dates=event_list),
            use_container_width=True,
        )
        returns_df = compute_return_features(prices["brent"].dropna()) if "brent" in prices.columns else pd.DataFrame()
        if not returns_df.empty:
            st.plotly_chart(
                plot_price_with_vol(prices, returns_df["vol_21d"]),
                use_container_width=True,
            )
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Price Summary")
            st.dataframe(prices.describe().round(2))
        with col2:
            if not returns_df.empty:
                st.subheader("Return Summary")
                st.dataframe(returns_df.describe().round(4))

# ─── Tab 2: Curve & Spreads ───────────────────────────────────────────────────
with tab_curve:
    if curve.empty:
        st.info("No curve data loaded.")
    else:
        spreads = build_spread_panel(prices, curve)
        if not spreads.empty:
            st.plotly_chart(plot_calendar_spreads(spreads), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(plot_curve_snapshot(curve), use_container_width=True)
        with col2:
            curve_met = compute_curve_metrics(curve, spreads)
            if not curve_met.empty:
                st.plotly_chart(
                    plot_curve_structure_by_year(curve_met), use_container_width=True
                )
        if not spreads.empty:
            st.subheader("Spread Summary Statistics")
            st.dataframe(spread_summary_stats(spreads))

# ─── Tab 3: Event Study ───────────────────────────────────────────────────────
with tab_events:
    if events_df.empty:
        st.info(
            "No events loaded. Populate `data/raw/manual_events.csv` with your "
            "geopolitical event list (date, label, category, description, direction)."
        )
    else:
        st.subheader("Event List")
        st.dataframe(events_df, use_container_width=True)

        if not prices.empty and "brent" in prices.columns:
            from src.analytics.returns import log_returns
            from src.analytics.event_study import Event, EventStudyConfig, run_event_study, summary_by_direction, average_event_profile

            brent_rets = log_returns(prices["brent"].dropna())
            ev_objects = [
                Event(
                    date=pd.Timestamp(row["date"]),
                    label=str(row.get("label", "")),
                    direction=str(row.get("direction", "")),
                )
                for _, row in events_df.iterrows()
            ]
            cfg = EventStudyConfig()
            es_df = run_event_study(brent_rets, ev_objects, cfg)

            st.subheader("Event Study Results (Brent Log Returns)")
            display_cols = [c for c in es_df.columns if "car" in c or c in ("event_date", "label", "direction")]
            st.dataframe(es_df[display_cols].round(4), use_container_width=True)

            for horizon in [1, 3, 5]:
                col = f"brent_car_{horizon}d"
                if col in es_df.columns:
                    st.plotly_chart(
                        plot_event_scatter(es_df, ret_col=col),
                        use_container_width=True,
                    )
                    summary = summary_by_direction(es_df, col)
                    if not summary.empty:
                        st.caption(f"Significance table — {col}")
                        st.dataframe(summary)

# ─── Tab 4: Regime ────────────────────────────────────────────────────────────
with tab_regime:
    if prices.empty or "brent" not in prices.columns:
        st.info("No price data for regime detection.")
    else:
        from src.analytics.returns import log_returns, rolling_vol
        from src.analytics.regime_model import fit_and_predict, regime_summary

        brent_ret = log_returns(prices["brent"].dropna())
        vol_5d    = rolling_vol(brent_ret, window=5, annualise=True)

        spreads_for_regime = (
            build_spread_panel(prices, curve) if not curve.empty else pd.DataFrame()
        )
        m1m3 = spreads_for_regime["M1_M3"] if "M1_M3" in spreads_for_regime.columns else None

        with st.spinner("Fitting regime model..."):
            regime_df = fit_and_predict(brent_ret, vol_5d, spread_m1_m3=m1m3)

        if not regime_df.empty:
            st.plotly_chart(
                plot_regime_overlay(prices["brent"], regime_df["regime_label"]),
                use_container_width=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Regime Distribution")
                counts = regime_df["regime_label"].value_counts()
                st.dataframe(
                    pd.DataFrame({"count": counts, "pct": (counts / len(regime_df) * 100).round(1)})
                )
            with col2:
                st.subheader("Regime Feature Means")
                st.dataframe(regime_summary(regime_df))

# ─── Tab 5: Scenarios ─────────────────────────────────────────────────────────
with tab_scenarios:
    if prices.empty or "brent" not in prices.columns:
        st.info("No price data for scenario engine.")
    else:
        spreads_for_scenario = (
            build_spread_panel(prices, curve) if not curve.empty else pd.DataFrame()
        )
        m1m3_scen = spreads_for_scenario.get("M1_M3", None) if not spreads_for_scenario.empty else None

        results = run_all_scenarios(
            prices["brent"].dropna(),
            spread_m1_m3=m1m3_scen,
        )

        st.subheader("Scenario Summary Table")
        st.dataframe(scenarios_to_table(results), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(plot_scenario_ranges(results), use_container_width=True)
        with col2:
            st.plotly_chart(plot_fan_chart(results, current_price=float(prices["brent"].dropna().iloc[-1])), use_container_width=True)

        st.plotly_chart(plot_scenario_distributions(results), use_container_width=True)

        st.subheader("Scenario Descriptions")
        for r in results:
            with st.expander(r["label"]):
                st.write(r["description"])
                cols = st.columns(4)
                cols[0].metric("Prior Prob.", f"{r['probability_prior']:.0%}" if r["probability_prior"] == r["probability_prior"] else "N/A")
                cols[1].metric("Brent Low", f"${r['brent_lo']:.1f}")
                cols[2].metric("Brent Central", f"${r['brent_central']:.1f}")
                cols[3].metric("Brent High", f"${r['brent_hi']:.1f}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Data: LSEG Workspace (LCOc1–LCOc12, CLc1). "
    "This dashboard is for analytical purposes only — not investment advice. "
    "Scenario ranges reflect explicit assumptions, not statistical forecasts."
)
