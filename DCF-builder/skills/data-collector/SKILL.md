---
name: data-collector
description: Gather and normalize A-share company, market, and macro inputs for DCF modeling.
allowed-tools: web_search read_file write_file
---

# Data Collector

Use iFind MCP tools first for all financial and trading data. Collect:

- Company identity, ticker, exchange, currency, fiscal year end.
- Three to five years of revenue, EBIT or NOPAT, D&A, CapEx, NWC change, debt, cash, and diluted shares.
- Latest price, market cap, beta or risk proxy, risk-free rate, credit/rate context, and tax assumptions.
- Four to eight comparable companies with revenue, EBITDA, net income, market cap, enterprise value, and source strings.

If a number cannot be sourced, mark it `[UNSOURCED]` and request or state an explicit assumption.
