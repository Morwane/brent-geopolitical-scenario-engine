# Implementation Notes and Assumptions

## Data Access

### Confirmed accessible (smoke test + full discovery, 2026-04-21)

| Instrument | RIC | Field | Rows (30-day test) |
|---|---|---|---|
| Brent M1 | LCOc1 | TRDPRC_1 | 20 |
| Brent M2 | LCOc2 | TRDPRC_1 | 20 |
| Brent M3 | LCOc3 | TRDPRC_1 | 20 |
| Brent M6 | LCOc6 | TRDPRC_1 | 20 |
| Brent M12 | LCOc12 | TRDPRC_1 | 19 |
| WTI M1 | CLc1 | TRDPRC_1 | 21 |
| S&P 500 | .SPX | TRDPRC_1 | confirmed |
| News API | ld.news.get_headlines | — | confirmed |

### Not accessible in this environment

| Instrument | RIC | Reason |
|---|---|---|
| US Dollar Index | DXY | Entitlement not available |
| US 10Y Treasury | US10YT=RR | Entitlement / RIC format issue |

## Methodology Assumptions

### Event Study
- Normal return is estimated as the arithmetic mean of the 20 trading days preceding the event.
- CAR (Cumulative Abnormal Return) = actual cumulative return − expected return (normal × horizon).
- The event list in `data/raw/manual_events.csv` is manually curated from public sources. It is not systematically complete — it covers major identified events only.

### Regime Detection
- Three regimes: calm, controlled tension, escalation.
- Primary method: Gaussian Hidden Markov Model (hmmlearn). Requires `pip install hmmlearn`.
- Fallback: deterministic volatility percentile classifier (no additional dependencies).
- State ordering uses mean 5-day volatility — the lowest-vol state is labelled "calm", the highest is "escalation".

### Scenario Engine
- Scenarios represent explicit analytical assumptions, not statistical forecasts.
- Ranges are parameterised in `config/scenarios.yaml` and document the economic reasoning.
- Monte Carlo simulation adds noise within each scenario's return range to produce a distribution rather than a point estimate. The noise scale is 5% of the range width × volatility multiplier.
- Probability priors sum to 1.0 and are illustrative — they are analytical inputs, not calibrated model outputs.

### News Factor
- Keyword-based scoring is transparent and interpretable, but misses nuance.
- Escalation and de-escalation keyword lists are in `src/analytics/news_factor.py`.
- The geo_shock_score is a rolling z-score of the smoothed net keyword count. Values near 0 are baseline; strongly positive values indicate unusual escalation signal.

### Macro Proxies
- DXY and US10YT=RR were not accessible under the current LSEG entitlement.
- SPX is accessible and can be used as a risk-off proxy where relevant.
- All macro data is treated as optional enrichment. The core event study and scenario engine run without it.

## Limitations
- The event study relies on a manually curated event list. Completeness depends on the user's curation.
- The scenario engine uses parameterised assumptions — updating parameters requires economic judgment, not just data.
- The HMM regime model is fitted in-sample. Out-of-sample regime classification should be validated carefully.
- News headline availability depends on LSEG entitlement tier. If the API is unavailable, the geo_shock_score will be zero or missing.
- Brent M12 may have fewer trading days than M1-M3 due to liquidity. Missing values are excluded from spread calculations.
