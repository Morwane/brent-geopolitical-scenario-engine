# Project Brief

## Project title

**Brent Under Geopolitical Stress: Event-Driven Forecasting and Scenario Engine with LSEG Pricing and News Data**

## Repository name

`brent-geopolitical-scenario-engine`

## Executive summary

This project studies how Brent crude oil reacts to recent geopolitical stress, especially around Iran, the Strait of Hormuz, sanctions, military escalation, de-escalation headlines, and OPEC+ responses.

The goal is **not** to build a generic “predict Brent with ML” project.

The goal is to build a professional market analysis and scenario engine that:
- analyzes Brent outright price behavior
- analyzes curve structure and calendar spreads
- extracts a geopolitical shock signal from LSEG news data
- detects market regimes
- projects multiple forward scenarios using explicit assumptions

## Main business question

How does Brent react, in both outright price and curve structure, to geopolitical stress, and how can those reactions be translated into forward market scenarios under Iran/Hormuz-related developments?

## Key outputs

The project should produce:
- event study tables and charts
- Brent curve diagnostics
- calendar spread diagnostics
- a daily geopolitical shock score
- regime classification
- scenario-based price and spread ranges
- a dashboard for visual inspection

## Why this is a strong project

This is stronger than a simple forecasting project because it links:
- geopolitical headlines
- supply risk
- shipping risk
- curve repricing
- outright price moves
- scenario logic

It is suitable for:
- commodities interviews
- macro / trading interviews
- market risk / research discussions
- GitHub portfolio presentation

## Core methodological pillars

1. **Event study** around identified geopolitical events
2. **Curve diagnostics** using Brent maturities and spreads
3. **News-based geopolitical factor**
4. **Regime detection**
5. **Scenario engine** with explicit assumptions

## Scenarios to include

At minimum:
1. de-escalation
2. persistent tension
3. severe escalation
4. escalation partly offset by supply response / OPEC+

## Output philosophy

Do not output only a single target price.
Prefer:
- ranges
- scenario tables
- fan charts
- conditional projections

