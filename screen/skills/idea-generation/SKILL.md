---
name: idea-generation
description: "Systematic A-share and Hong Kong stock screening and investment idea sourcing. Combines iFind-driven quantitative screens, China market structure checks, thematic research, and red-flag review to surface long, short, event-driven, value, quality, growth, dividend, and turnaround ideas."
tags:
  - china-equity
  - stock-screening
  - idea-generation
  - ifind
allowed-tools: create_task_output_dir write_markdown_report write_json_artifact
---

# Idea Generation

## Workflow

### Step 1: Define Search Criteria

Ask only for missing parameters that materially change the screen:

- **Direction**: long, short, long/short pair, watchlist, or both long and short
- **Market**: A-share, Hong Kong, Stock Connect, China ADR/global comps, or cross-market
- **Universe**: index, sector, theme, market cap, liquidity, listing board, region, ownership type
- **Style**: value, growth, quality, dividend, event-driven, distressed turnaround, policy catalyst, short-risk
- **Exclusions**: ST/*ST, suspended stocks, newly listed stocks, loss-making names, low liquidity, pending delisting risk
- **Time horizon**: trade, 1-3 months catalyst, 6-12 months fundamental idea, multi-year compounder

If the user gives usable criteria, run the screen directly and document assumptions.

### Step 2: Build the China/HK Universe

Use iFind first. Define and document:

- Listing venue: SSE, SZSE, BSE, HKEX, ADR/global comparable
- Tradability: active trading status, suspension/resumption, Stock Connect eligibility, short-selling eligibility where relevant
- Market structure: A-share daily price limits, ST/*ST status, delisting warning, price-limit lock risk
- Liquidity: turnover, ADV, free-float market cap, bid/ask or turnover proxy
- Calendar: latest trading day, reporting period, holiday effects, financial reporting season

Mark unknown fields as `[UNSOURCED]`.

### Step 3: Quantitative Screens

Run factor screens based on the requested style.

**Value Screen**
- PE/PB/PS/EV EBITDA below sector or historical median
- Dividend yield or buyback yield above market/sector average
- Free-cash-flow yield, operating cash conversion, net cash balance
- Valuation discount with identifiable catalyst, not just low multiple

**Growth Screen**
- Revenue and net-profit growth, forecast growth, order backlog where available
- Margin expansion, ROE/ROIC improvement, operating leverage
- Industry demand indicators from EDB/index/news where relevant
- Avoid growth built on receivables, inventory, subsidies, or aggressive capitalization

**Quality Screen**
- ROE/ROIC stability, gross/operating margin resilience, cash conversion
- Balance-sheet strength, low pledge ratio, low contingent liability signals
- Governance quality, audit opinions, regulatory penalties, exchange inquiries
- Consistent disclosure and shareholder-return record

**Dividend/Income Screen**
- Dividend yield, payout ratio, dividend continuity, free cash flow coverage
- State-owned-enterprise reform and market-value-management catalysts
- Interest-rate, credit-spread, and bond-yield context when useful

**Event-Driven Screen**
- Restricted-share unlocks, earnings previews, profit alerts/warnings, buybacks
- M&A/restructuring, refinancing, spin-offs, asset injections, policy windows
- Management/major-holder changes, share pledges, regulatory inquiries
- Estimate catalyst date, evidence, and downside if catalyst fails

**Distressed Turnaround Screen**
- Loss narrowing, debt restructuring, asset sales, order recovery, policy support
- ST removal possibility, delisting-risk mitigation, liquidity and suspension risk
- Explicitly separate turnaround evidence from hope

**Short/Risk Screen**
- Deteriorating revenue/profit, margin compression, receivables/inventory build
- Cash-flow divergence from profit, high pledge ratio, frequent related-party deals
- Valuation premium without support, crowded theme exhaustion, unlock overhang
- Regulatory inquiry, auditor change, restatement, penalty, profit warning
- Borrow/shortability, squeeze risk, price-limit/suspension risk, policy rescue risk

### Step 4: Thematic Sweep

For themes, map the chain before picking stocks:

1. Define policy, demand, technology, or supply-chain thesis.
2. Identify direct beneficiaries, second-order beneficiaries, and likely losers.
3. Separate pure-play exposure from diversified exposure.
4. Check if the theme is already priced in using valuation, momentum, ownership/flow, and news intensity.
5. Prefer underappreciated links with measurable evidence and near-term catalysts.

### Step 5: Idea Presentation

For each candidate:

**[Company Name] ([Ticker]) - [Long/Short/Watch] - [One-line thesis]**

| Metric | Value | Peer/History Context | Source |
| --- | --- | --- | --- |
| Market cap / free float | | | |
| Valuation | | | |
| Growth | | | |
| Quality / cash flow | | | |
| Dividend / shareholder return | | | |
| Liquidity / tradability | | | |
| Catalyst | | | |
| China-market risk flags | | | |

Then provide:

- **Why it screened in**: 3-5 factual signals
- **What may be mispriced**: hypothesis, not conclusion
- **Catalyst path**: expected event/date/source
- **What would make it wrong**: fundamental, policy, liquidity, governance, and market-structure risks
- **Next diligence**: model, filings, channel checks, management call, peer comparison, or short-borrow check

### Step 6: Output Artifacts

Use local tools when the user asks for deliverables or when the screen is substantial:

- `write_markdown_report`: methodology, ranked shortlist, tables, idea notes, risk appendix
- `write_json_artifact`: machine-readable criteria, candidates, scores, source fields, risk flags
- `create_task_output_dir`: return the shared task directory under `out/<YYYYMMDD-HHMMSS>/`

## Important Notes

- Screens generate candidates, not investment conclusions.
- Use iFind first and include as-of dates. Any unsupported data must be marked `[UNSOURCED]`.
- Do not hide China-specific risks: ST/delisting, suspensions, limit-up/limit-down, unlocks, pledge risk, Stock Connect flows, margin financing, regulatory inquiry, profit warnings, and policy shifts.
- For shorts, require stronger evidence and explicitly disclose borrow/squeeze/suspension/price-limit risk.
- Contrarian and turnaround ideas need a catalyst; cheap without a catalyst is usually a watchlist item.
- Keep a record of excluded names and failed criteria so the shortlist is auditable.

