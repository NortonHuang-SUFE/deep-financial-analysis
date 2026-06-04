---
name: valuation-methodologies
description: Core valuation methodology skill for Task 3, covering DCF, trading comps, precedent transactions, reconciliation, method weights, valuation range, and sanity checks.
---

# Valuation Methodologies

Use this skill whenever Task 3 performs valuation analysis for a single-stock
coverage run. This is the required methodology reference for:

- Discounted Cash Flow analysis.
- Trading comparable companies analysis.
- Precedent transactions analysis.
- Valuation reconciliation and method weights.
- Valuation range and sanity checks.

## General Rules

- Use at least DCF and trading comps for a successful Task 3 valuation.
- Use precedent transactions when M&A relevance is high or enough comparable
  transaction evidence exists.
- Always produce a valuation range: Low, Base, and High.
- Always explain method weights.
- Always reconcile conflicts across methods.
- Always cite source strings and market data dates.
- Mark unsupported items `[UNSOURCED]`; do not fabricate missing figures.

## DCF Analysis

DCF is the intrinsic-value method. It should reflect the audited Task 3
assumption pack and consume Task 2 integrated-model outputs.

Required inputs:

- Revenue by year from the Task 2 revenue build or sourced Task 3 update.
- EBIT or EBITDA and tax rate.
- D&A.
- CapEx.
- Change in NWC.
- Debt, cash, non-operating assets, minority interest, preferred stock, and
  diluted shares.
- WACC components.
- Terminal growth or exit multiple.
- Bear/Base/Bull scenario assumptions.

Core formulas:

```text
NOPAT = EBIT x (1 - Tax Rate)
Unlevered FCF = NOPAT + D&A - CapEx - Change in NWC
Terminal Value = FCF(final year) x (1 + g) / (WACC - g)
Enterprise Value = PV(Projected FCF) + PV(Terminal Value)
Equity Value = Enterprise Value - Net Debt + Non-operating Assets
Price per Share = Equity Value / Diluted Shares
```

DCF requirements:

- WACC must use market-value capital structure where possible.
- Cost of equity should use a defensible risk-free rate, beta, and equity risk
  premium.
- Cost of debt should reflect current borrowing cost, traded debt yield, credit
  spread, or justified proxy.
- Terminal growth must be lower than WACC and consistent with long-run industry
  maturity.
- Terminal value share of EV must be calculated and explained, especially if it
  exceeds 60-70%.
- Sensitivity analysis must include WACC vs. terminal growth and at least one
  operating sensitivity such as revenue CAGR vs. terminal margin.
- Bear/Base/Bull cases must represent real operating paths, not cosmetic
  tweaks.

Common DCF failure modes to check:

- Revenue growth without matching investment in CapEx or working capital.
- High terminal growth for a mature or cyclical business.
- Using net income instead of unlevered FCF.
- Mixing levered cash flows with WACC.
- Missing share dilution or net debt bridge.
- Unexplained break from historical margins.

## Trading Comparables

Trading comps are the market-relative valuation method. They show how public
markets price similar companies today.

Peer selection criteria:

- Same or adjacent industry.
- Similar business model and revenue streams.
- Similar growth, margins, capital intensity, geography, and customer exposure.
- Comparable size and liquidity when possible.
- Clear explanation for each peer included or excluded.

Required peer data:

- Stock price and market data date.
- Diluted shares and market capitalization.
- Debt, cash, minority interest, preferred stock, and enterprise value.
- LTM revenue, EBITDA, EBIT, net income.
- NTM estimates when available.
- Growth, margin, leverage, and return metrics relevant to the sector.

Required multiples:

- EV/Revenue when revenue scale matters or profitability is weak.
- EV/EBITDA for mature operating businesses and capital-intensive sectors.
- EV/EBIT when D&A differs meaningfully across peers.
- P/E for profitable companies with comparable capital structures.
- Sector-specific multiples when relevant, such as P/B for financials.

Required workbook/table content:

- 5-10 peers when data availability allows.
- Peer rationale.
- LTM and forward multiples.
- Outlier handling.
- Statistical summary: maximum, 75th percentile, median, 25th percentile,
  minimum.
- Target premium/discount rationale based on growth, margin, risk, scale,
  liquidity, market position, and geography.

Application:

- Apply selected multiple range to target financial metrics.
- Convert enterprise value to equity value through net debt and other claims.
- Convert equity value to price per diluted share.
- Use a range, typically 25th percentile / median / 75th percentile or a
  justified adjusted range.

## Precedent Transactions

Precedent transactions are the control-value and M&A reference method. Use them
only when they are relevant and supported by data.

Transaction selection criteria:

- Same or similar industry.
- Comparable business model and size.
- Recent enough to reflect relevant capital-market conditions, usually within
  the last 3-5 years.
- Announced and closed, or clearly explain why an announced pending deal is
  still useful.
- Strategic rationale, control premium, and synergy context are known.

Required transaction data:

- Announcement date and close date where available.
- Target and acquirer.
- Deal value, purchase price, and consideration mix.
- Target LTM revenue, EBITDA, EBIT, or relevant sector metric at transaction
  date.
- Transaction EV/Revenue, EV/EBITDA, EV/EBIT, or sector-specific multiples.
- Unaffected price and control premium for public targets where available.
- Strategic rationale and source strings.

Application:

- Apply selected transaction multiple range to target LTM or NTM metric.
- Explain control premium and why it should or should not affect the primary
  price target.
- Use lower weight when M&A is not a realistic near-term valuation anchor.
- If not applicable, state why and assign zero or sanity-check-only weight.

## Valuation Reconciliation

Reconciliation turns method outputs into a final valuation range and target.
It must not average numbers mechanically.

Required summary table:

```markdown
| Method | Low | Base | High | Weight | Rationale |
| --- | ---: | ---: | ---: | ---: | --- |
| DCF | | | | | |
| Trading Comps | | | | | |
| Precedent Transactions | | | | | |
| Historical Multiples | | | | | |
| Market-Implied Check | | | | | |
```

Weighting principles:

- DCF weight is higher when Task 1/2 evidence is strong and forecasts are
  reliable.
- Trading comps weight is higher when the peer set is clean and market pricing
  is credible.
- Precedent transactions weight is higher when the company or sector has clear
  M&A relevance.
- Historical multiples are usually a sanity check unless the company has a
  stable long trading history.
- Market-implied checks are usually diagnostic; they reveal what the current
  price already discounts.

The sum of primary method weights must equal 100%. If a method is used only as
a sanity check, label it and give it 0% primary weight.

## Sanity Checks

Run these checks before finalizing `valuation_analysis.md`:

- Historical multiple check: implied target multiple vs. company history.
- Peer premium/discount check: growth, margin, risk, scale, and market position
  justify the relative multiple.
- Market-implied growth check: current price-implied expectations vs. the
  assumption pack.
- IRR/implied return check: current price to target over the stated horizon.
- Market-cap reasonableness check: target market cap vs. peer and industry
  scale.
- Terminal value check: terminal value as percent of EV.
- WACC reasonableness check: components and final rate vs. business risk.
- Scenario check: Bear case is genuinely adverse and Bull case has evidence.
- Source check: no major valuation input lacks a source or `[UNSOURCED]`
  disclosure.

If sanity checks conflict with the headline target, either revise the target or
write the conflict plainly with a defensible rationale.
