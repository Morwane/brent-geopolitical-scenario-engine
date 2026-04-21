# Data and LSEG Rules

## Absolute rule

Do not invent accessible instruments, fields, or data coverage.

## Required approach

Before using any instrument aggressively in the project, validate it.

The code must include:
- discovery logic
- entitlement-aware validation
- fallback logic when a requested series is unavailable

## Instrument groups to explore

### Core market instruments
- Brent front-month
- Brent nearby maturities
- WTI front-month
- Brent-WTI relationship

### Curve and spread inputs
- Brent M1
- Brent M2
- Brent M3
- Brent M6
- Brent M12

### News inputs
Search around:
- Iran
- Strait of Hormuz
- sanctions
- escalation
- attacks
- ceasefire
- de-escalation
- OPEC+

### Macro / risk proxies
Use only what is accessible and relevant.
Examples may include:
- broad USD proxy
- equity/risk proxy
- volatility/risk-off proxy
- rates proxy

## Fallback philosophy

If some instruments are not accessible:
- degrade gracefully
- document the fallback
- do not break the entire project
- clearly label assumptions in README and code comments where necessary

## Event dataset rule

The project should maintain a structured event list for major geopolitical developments.
Each event should include:
- event date
- event label
- event category
- short description
- escalation vs de-escalation tag

## News factor rule

Start simple.
A transparent scoring framework is preferred before adding more advanced NLP.

Example components:
- headline count
- escalation keyword hits
- de-escalation keyword hits
- source or theme flags if accessible

## Quality rule

Processed datasets should be saved in a reproducible format such as:
- parquet
- csv

Each major loader should:
- log row counts
- log missingness
- validate index alignment
- avoid silent failures

## Honesty rule for outputs

Do not fabricate:
- scenario results
- backtest metrics
- performance claims
- charts that are not actually generated

