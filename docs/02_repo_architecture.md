# Repository Architecture

## Required structure

```text
brent-geopolitical-scenario-engine/
  README.md
  requirements.txt
  .env.example
  config/
    instruments.yaml
    fields.yaml
    scenarios.yaml
  data/
    raw/
    processed/
    outputs/
  notebooks/
    01_instrument_discovery.ipynb
    02_data_quality_check.ipynb
    03_event_study_iran_hormuz.ipynb
    04_curve_and_spread_diagnostics.ipynb
    05_news_geopolitical_factor.ipynb
    06_regime_detection.ipynb
    07_scenario_engine.ipynb
  src/
    __init__.py
    session.py
    discovery.py
    loaders/
      prices_loader.py
      futures_loader.py
      news_loader.py
      macro_loader.py
    analytics/
      returns.py
      spreads.py
      curve_metrics.py
      event_study.py
      regime_model.py
      scenario_engine.py
      probabilistic_projection.py
    visualization/
      plots_price.py
      plots_curve.py
      plots_event.py
      plots_scenarios.py
    utils/
      dates.py
      cleaning.py
      validation.py
      io.py
  app/
    streamlit_app.py
  tests/
    test_spreads.py
    test_event_study.py
    test_scenario_engine.py
```

## File responsibilities

### `src/session.py`
- initialize LSEG session
- read credentials from environment
- open / close session cleanly
- provide safe wrapper logic

### `src/discovery.py`
- identify which instruments are actually accessible
- validate requested instruments before use
- save inventory of working instruments and fields

### `src/loaders/prices_loader.py`
- pull Brent / WTI historical prices
- clean and align dates
- export processed outputs

### `src/loaders/futures_loader.py`
- retrieve Brent maturities if accessible
- build daily curve dataset
- support continuation / fallback logic

### `src/loaders/news_loader.py`
- pull relevant geopolitical headlines
- standardize timestamps
- create structured event/news dataset

### `src/loaders/macro_loader.py`
- load macro / risk proxies when available
- examples: DXY, VIX-style proxy, rates, other cross-market signals

### `src/analytics/returns.py`
- basic returns and volatility calculations

### `src/analytics/spreads.py`
- compute M1-M2, M1-M3, M1-M6, M6-M12, Brent-WTI
- reusable validation-safe functions

### `src/analytics/curve_metrics.py`
- backwardation / contango diagnostics
- slope / curvature type summaries if feasible

### `src/analytics/event_study.py`
- event window logic
- measure response on event day and post-event windows
- summary tables and reusable functions

### `src/analytics/regime_model.py`
- regime detection logic
- calm / controlled tension / escalation states
- interpretable approach preferred

### `src/analytics/scenario_engine.py`
- explicit scenario assumptions
- produce scenario tables and conditional projections

### `src/analytics/probabilistic_projection.py`
- optional probabilistic / quantile output helpers

### `app/streamlit_app.py`
- visual dashboard
- price history
- spread history
- event windows
- regime outputs
- scenario outputs

## Architecture rule

The repository must work as a real codebase, not as a notebook-only project.

