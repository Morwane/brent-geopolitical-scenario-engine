# Implementation Plan

## Goal

Build the repository in a clean order that reduces errors and prevents false assumptions.

## Phase 1 — Repository scaffold

Create first:
- folder structure
- `requirements.txt`
- `.env.example`
- config files
- starter `README.md`

## Phase 2 — Connectivity and validation

Build:
1. `src/session.py`
2. `src/discovery.py`

Required outcome:
- session can open safely
- instrument validation exists
- working inventory can be exported

## Phase 3 — Market data loaders

Build:
1. `src/loaders/prices_loader.py`
2. `src/loaders/futures_loader.py`
3. `src/loaders/news_loader.py`
4. `src/loaders/macro_loader.py`

Required outcome:
- load historical market data
- align dates
- save processed datasets

## Phase 4 — Core analytics

Build:
1. `src/analytics/returns.py`
2. `src/analytics/spreads.py`
3. `src/analytics/curve_metrics.py`
4. `src/analytics/event_study.py`

Required outcome:
- reusable analytics functions
- clean event window outputs
- spread and curve diagnostics

## Phase 5 — Regime and scenarios

Build:
1. `src/analytics/regime_model.py`
2. `src/analytics/scenario_engine.py`
3. `src/analytics/probabilistic_projection.py`

Required outcome:
- regime assignment or probabilities
- explicit scenario logic
- projected ranges, not only point estimates

## Phase 6 — Visualization and app

Build:
1. plotting utilities
2. Streamlit dashboard

Required outcome:
- price charts
- spread charts
- event overlays
- regime view
- scenario view

## Phase 7 — Documentation and tests

Finalize:
- README
- tests
- assumptions note
- notebook templates

## Important implementation discipline

First get:
- validated data
- clean loaders
- event study
- spreads
- scenario framework

Then add:
- regime logic
- supporting ML

