# Assumption Pack Reference

Use this reference when drafting the final DCF assumption pack.

## Required Sections

Return one Markdown document with exactly these top-level sections:

1. `## 假设背景`
2. `## 假设逻辑`
3. `## 假设结果`

## 假设背景

Summarize:

- Target company identity, business model, latest historical base year, unit,
  and reporting currency.
- Comparable companies and useful peer ranges.
- Industry, macro, rate, news, and announcement context from iFind.
- Important sourced data and `[UNSOURCED]` gaps.

## 假设逻辑

Explain:

- Revenue segmentation by products, segments, regions, channels, or customers.
- Segment-level Bear/Base/Bull logic and how segment assumptions aggregate into
  total revenue assumptions.
- Logic for EBIT margin, tax rate, D&A/revenue, CapEx/revenue, NWC/delta
  revenue, WACC, and terminal growth.
- How assumptions reconcile with target history, peers, market data, and
  industry evidence.

## 假设结果

The result does not have to be JSON. It must contain enough explicit data for
the parent agent to populate `dcf_json.scenarios` for `build_dcf_model`.

Include Bear/Base/Bull assumption data for:

- `revenue_growth`: preferably five annual values, or enough segment-level
  values for the parent to derive five annual total growth rates.
- `ebit_margin`: preferably five annual values.
- `tax_rate`.
- `da_pct_revenue`.
- `capex_pct_revenue`.
- `nwc_pct_delta_revenue`.
- `wacc`.
- `terminal_growth`.
- Source strings for the assumptions.

Use decimals such as `0.055` or clearly labeled percentages such as `5.5%`.
Keep terminal growth lower than WACC. If any field is not directly sourced,
state the assumption and mark it `[UNSOURCED]`.
