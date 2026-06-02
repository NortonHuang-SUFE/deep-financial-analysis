---
name: dcf-assumption-generation
description: Generate A-share DCF Bear/Base/Bull assumptions using iFind company, peer, industry, macro, news, and announcement data.
---

# DCF Assumption Generation

Use this skill when producing DCF assumptions for an A-share company. The goal
is to turn the parent agent's collected evidence plus focused iFind follow-up
research into scenario assumption data that the parent agent can use while
building `dcf_json` for `build_dcf_model`.

## Workflow

1. Understand the company and comparable companies from the input.
   - Identify business model, revenue base, margin base, peer ranges, and data
     gaps.

2. Use tools to understand the industry.
   - Prefer iFind A-share stock/company data, iFind EDB economic indicators,
     and iFind news or announcements.
   - Look for demand, pricing, capacity, regulation, cost, macro, and peer
     disclosure signals.

3. Break down revenue before forecasting.
   - Split revenue by the company's economically meaningful segments, products,
     regions, channels, or customer groups whenever the input or iFind data
     supports it.
   - Example: if Company A has three products, forecast the three products
     separately in Bear/Base/Bull, then combine them into total revenue growth.
   - If segment-level data is incomplete, use the best sourced split and mark
     gaps `[UNSOURCED]`.

4. Use tools to fill gaps in the split.
   - Gather segment size, historical growth, volume/price indicators, peer
     segment trends, and relevant macro or industry series.
   - Convert the split forecast into total revenue growth data for
     Bear/Base/Bull.

5. Build the remaining Bear/Base/Bull assumptions.
   - Use target history and peer ranges for `ebit_margin`, `da_pct_revenue`,
     `capex_pct_revenue`, and `nwc_pct_delta_revenue`.
   - Use tax disclosures or statutory context for `tax_rate`.
   - Use market data, rates, beta or peer risk, debt cost, and risk context for
     `wacc`.
   - Use long-run nominal growth, sector maturity, and reinvestment needs for
     `terminal_growth`; it must be lower than WACC.

## References

- Read `references/assumption-pack.md` before drafting the final answer. It
  defines the required Markdown sections and assumption data checklist.

Do not force the final result into JSON. Use tables or structured bullets when
they communicate the assumption data more clearly.
