---
name: dcf-model
description: Prepare DCF assumptions and call build_dcf_model for deterministic Excel generation.
allowed-tools: build_dcf_model validate_dcf_model
---

# DCF Model

Prepare `dcf_json` with:

- `company`, `ticker`, `currency`, `unit`, `fiscal_year_end`.
- `historicals`: 3-5 annual records with revenue, EBIT or EBIT margin, D&A, CapEx, NWC change, debt, cash, shares, and source.
- `market_data`: current price, beta, risk-free rate, equity risk premium, pre-tax cost of debt, tax rate, debt, cash, shares, and source.
- `scenarios`: Bear, Base, Bull assumptions for revenue growth, EBIT margin, tax, D&A percentage of revenue, CapEx percentage of revenue, NWC percentage of delta revenue, WACC, and terminal growth.
- `comps_summary`: peer medians and ranges used as sanity checks.

Use the `dcf-assumption-researcher` output as assumption evidence, not as the only source. Build final `scenarios` from the subagent pack plus the historicals, market data, comps, industry/news context, and any documented `[UNSOURCED]` assumptions.

After building the workbook, run `validate_dcf_model` and surface any warning.
