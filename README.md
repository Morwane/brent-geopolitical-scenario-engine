# Brent Under Geopolitical Stress
## Event-Driven Forecasting and Scenario Engine with LSEG Pricing and News Data

---

## Business Framing

Brent crude is not priced purely on supply and demand fundamentals.
It carries a persistent geopolitical risk premium — particularly around
Iran, the Strait of Hormuz, sanctions, and OPEC+ response dynamics.

This project builds a professional analytical framework for studying how
Brent reacts to geopolitical shocks, both in outright price and in
forward curve structure, and for projecting multiple forward scenarios
under explicit geopolitical assumptions.

**Core question:**
> How does Brent crude — in both flat price and curve structure — respond to geopolitical stress events, and how can we project scenario-conditional price and spread ranges under Iran/Hormuz-related developments?

---

## Project Objective

This is **not** a generic "predict Brent with ML" project.

It is an **event-driven market analysis and scenario engine** that combines:

1. **Event study** — quantify Brent reactions (outright + spreads) around identified geopolitical events
2. **Curve diagnostics** — track backwardation/contango dynamics as supply risk proxies
3. **News-based geopolitical factor** — transparent keyword scoring of LSEG headlines
4. **Regime detection** — classify market state (calm / tension / escalation) using HMM
5. **Scenario engine** — project Brent ranges and spread behaviour under four explicit scenarios

---

## Methodology

### 1. Event Study
- Events: manually curated list of Iran/Hormuz/sanctions/OPEC+ events
- Metric: Cumulative Abnormal Return (CAR) — actual return minus estimated normal return
- Estimation window: 20 trading days pre-event
- Post-event horizons: +1d, +3d, +5d, +10d
- Series studied: Brent outright, M1-M3 spread, Brent-WTI

### 2. Curve Diagnostics
- Instruments: LCOc1 through LCOc12 (all confirmed accessible via LSEG TRDPRC_1)
- Spreads: M1-M2, M1-M3, M1-M6, M6-M12, Brent-WTI
- Metrics: curve slope, backwardation/contango classification, rolling % in backwardation

### 3. Geopolitical Shock Score
- Transparent keyword-counting on LSEG news headlines
- Daily escalation hit count minus de-escalation hit count
- Rolling z-score for cross-time comparability

### 4. Regime Detection
- Gaussian Hidden Markov Model on: Brent log return, 5-day vol, M1-M3 spread, geo_shock_score
- Three states: calm, controlled tension, escalation
- Fallback to volatility percentile classifier if hmmlearn unavailable

### 5. Scenario Engine
Four explicit scenarios with economic reasoning:

| Scenario | Brent Return Range | M1-M3 Change | Prior Prob. |
|---|---|---|---|
| De-escalation | −15% to −5% | −$2.0 to −$0.5 | 25% |
| Persistent Tension | −5% to +5% | −$0.5 to +$0.5 | 40% |
| Severe Escalation | +10% to +30% | +$1.5 to +$5.0 | 20% |
| Escalation + OPEC+ Response | +3% to +15% | +$0.5 to +$2.5 | 15% |

---

## Data Validation Status

All instruments validated via live LSEG Workspace session (2026-04-21):

| Instrument | RIC | Status | Field |
|---|---|---|---|
| Brent M1 | LCOc1 | ✅ Accessible | TRDPRC_1 |
| Brent M2 | LCOc2 | ✅ Accessible | TRDPRC_1 |
| Brent M3 | LCOc3 | ✅ Accessible | TRDPRC_1 |
| Brent M6 | LCOc6 | ✅ Accessible | TRDPRC_1 |
| Brent M12 | LCOc12 | ✅ Accessible | TRDPRC_1 |
| WTI M1 | CLc1 | ✅ Accessible | TRDPRC_1 |
| S&P 500 | .SPX | ✅ Accessible | TRDPRC_1 |
| News API | ld.news | ✅ Accessible | get_headlines |
| DXY | DXY | ❌ Unavailable | — |
| US 10Y | US10YT=RR | ❌ Unavailable | — |

---

## Repository Structure

```
brent-geopolitical-scenario-engine/
├── README.md
├── ASSUMPTIONS.md           ← methodology notes and data limitations
├── requirements.txt
├── .env.example
├── config/
│   ├── instruments.yaml     ← candidate RICs with validation status
│   ├── fields.yaml          ← LSEG field priority configuration
│   └── scenarios.yaml       ← scenario parameters
├── data/
│   ├── raw/                 ← manual_events.csv lives here
│   ├── processed/           ← parquet/csv outputs from loaders
│   └── outputs/             ← scenario summary tables
├── src/
│   ├── session.py           ← LSEG session (Workspace-first, APP_KEY fallback)
│   ├── discovery.py         ← instrument + field validation
│   ├── loaders/
│   │   ├── prices_loader.py
│   │   ├── futures_loader.py
│   │   ├── news_loader.py
│   │   └── macro_loader.py
│   ├── analytics/
│   │   ├── returns.py
│   │   ├── spreads.py
│   │   ├── curve_metrics.py
│   │   ├── event_study.py
│   │   ├── news_factor.py
│   │   ├── regime_model.py
│   │   ├── scenario_engine.py
│   │   └── probabilistic_projection.py
│   ├── visualization/
│   │   ├── plots_price.py
│   │   ├── plots_curve.py
│   │   ├── plots_event.py
│   │   └── plots_scenarios.py
│   └── utils/
│       ├── dates.py
│       ├── cleaning.py
│       ├── validation.py
│       └── io.py
├── app/
│   └── streamlit_app.py     ← interactive dashboard
├── notebooks/
│   ├── 01_instrument_discovery.ipynb
│   ├── 02_data_quality_check.ipynb
│   ├── 03_event_study_iran_hormuz.ipynb
│   ├── 04_curve_and_spread_diagnostics.ipynb
│   ├── 05_news_geopolitical_factor.ipynb
│   ├── 06_regime_detection.ipynb
│   └── 07_scenario_engine.ipynb
└── tests/
    ├── test_spreads.py
    ├── test_event_study.py
    └── test_scenario_engine.py
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Validate LSEG access

```bash
python -m src.discovery
```

This probes all candidate instruments and saves `data/processed/instrument_inventory.csv`.

### 3. Load market data

```python
from src.session import managed_session
from src.loaders.prices_loader import load_prices
from src.loaders.futures_loader import load_curve

with managed_session():
    prices = load_prices("2022-01-01", "2026-04-21")
    curve  = load_curve("2022-01-01", "2026-04-21")
```

### 4. Run the dashboard

```bash
streamlit run app/streamlit_app.py
```

### 5. Run tests

```bash
pytest tests/ -v
```

---

## Key Outputs

- **Event study tables**: CAR by direction (escalation vs de-escalation) at +1d, +3d, +5d, +10d
- **Curve diagnostics**: spread time series, backwardation/contango regime by year
- **Geopolitical shock score**: daily score from LSEG headlines
- **Regime classification**: calm / controlled tension / escalation
- **Scenario projections**: Brent price ranges and spread change ranges under four scenarios
- **Fan chart**: probability-weighted blended distribution across scenarios

---

## Limitations

- The event list is manually curated and not systematically complete.
- Scenario parameters are analytical assumptions — not calibrated statistical outputs.
- The HMM regime model is fitted in-sample. It should be validated before any forward use.
- DXY and US 10Y Treasury are not accessible in this LSEG environment. Macro context relies on SPX only.
- All scenario outputs are ranges. Do not use point estimates in isolation.

---

## Why This Project Is Relevant

For **commodities / energy trading** roles:
- Shows understanding of physical supply risk (Hormuz, sanctions, OPEC+)
- Demonstrates curve structure intuition (backwardation as a supply stress signal)
- Links geopolitical headlines to market microstructure

For **macro / global markets** roles:
- Integrates news signal, regime detection, and scenario analysis
- Multi-scenario projection with explicit economic logic is standard sell-side practice

For **market risk** roles:
- Event study methodology is directly applicable to risk attribution
- Scenario engine maps to standard stress-testing frameworks

---

*Data source: LSEG Workspace (lseg-data 2.1.1). Instruments confirmed accessible 2026-04-21.*
*This project is for analytical and portfolio purposes. Not investment advice.*
