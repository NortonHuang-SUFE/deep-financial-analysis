---
name: valuation-reconciliation
description: Multi-method valuation reconciliation table with weights and sanity checks.
---

# Valuation Reconciliation

Use this skill to synthesize all valuation methods into a single reconciliation table, assign weights, compute a price target range, and run mandatory sanity checks. This is Step 3.6 of the Task 3 workflow.

The reconciliation table must be produced even when some methods are not available. If a method cannot be run, record it in the table with "N/A" and explain why.

## The Five-Method Reconciliation Table

Produce a table with the following structure. All values in the same currency (report in local currency and convert if needed). Low/Base/High refer to Bear/Base/Bull scenario outputs from DCF, and equivalent low/mid/high ranges from comps and precedent.

| Method | Low | Base | High | Weight | Rationale |
|--------|-----|------|------|--------|-----------|
| DCF | | | | | |
| Trading Comps | | | | | |
| Precedent Transactions | | | | | |
| Historical Multiples | | | | | |
| Market-Implied Check | | | | | |
| **Weighted Implied Price** | | | | | |

Express Low/Base/High as implied share prices (convert from EV using net debt and shares from `financial_facts.json`).

For the Weighted Implied Price row, compute: sum(Base_i × Weight_i) for i in all methods with non-zero weight.

## Weighting Principles

### DCF

Assign higher weight (40-60%) when:
- Task 1 research is thorough and `business_driver_map.json` is complete.
- Historical financials in `financial_facts.json` span at least 3 years with no major gaps.
- The business has stable, predictable cash flows.
- Assumption audit produced no FAIL items and few WARN items.

Assign lower weight (20-30%) when:
- The company is early-stage or pre-profit.
- Cash flows are highly volatile or cyclical.
- Terminal value exceeds 85% of EV (high sensitivity to terminal assumptions).
- Assumption audit produced multiple WARN items.

### Trading Comps

Assign higher weight (25-40%) when:
- A clean peer set of 4+ comparable companies exists with similar business model, geography, and growth profile.
- The market is pricing peers efficiently (no evidence of sector-wide mispricing).
- The company's own multiple history shows mean reversion to peer median.

Assign lower weight (10-20%) when:
- No truly comparable public peers exist.
- The peer set is distorted by M&A activity, delistings, or sector rotation.
- The company's business model is materially different from available peers.

### Precedent Transactions

Include in primary weighting (10-20%) only when:
- The company or sector has seen meaningful M&A activity in the last 3-5 years.
- There is a plausible near-term catalyst for corporate activity (privatization, strategic buyer, restructuring).
- Transactions are sufficiently comparable (similar geography, size, and business mix).

Otherwise, record precedent transactions for reference only with 0% primary weight.

### Historical Multiples

Use primarily as a sanity check (5-15% weight). Historical multiples inform where the stock has traded, not where it should trade. Assign higher weight only when:
- The current operating environment is similar to a historical period.
- There is evidence of mean reversion behavior in the stock's trading history.

### Market-Implied Check

This method does not produce a price target — it reverse-engineers what growth, margin, or return assumptions the current market price implies. Always include, but weight 0% in the blended target.

Use it to answer: "what does the current price assume about future performance, and is that reasonable?"

## How to Run Each Method

### DCF

Consume outputs from `dcf_model.xlsx` and `assumption_pack.md`. Use Bear/Base/Bull scenario outputs directly. Convert EV to implied share price: (EV - net debt) / diluted shares.

### Trading Comps

Source: `comps.xlsx`. Steps:
1. Apply the selected peer median (or mean if median is distorted) EV/EBITDA and P/E multiples to the company's NTM financials from `integrated_model.xlsx`.
2. Produce a Low/Base/High range using the 25th percentile, median, and 75th percentile of the peer set.
3. Apply a premium or discount vs. the peer median if justified by the company's growth, margin, or quality profile. Document the premium/discount assumption explicitly.

### Precedent Transactions

Source: `precedent_transactions.xlsx` (if applicable). Steps:
1. Apply transaction multiples (typically EV/EBITDA or EV/revenue) to LTM or NTM financials.
2. Control premiums in precedent transactions typically reflect a change-of-control premium; apply a haircut of 20-30% when using as a public market reference.

### Historical Multiples

Source: `financial_facts.json` and price history. Steps:
1. Compute the stock's own historical EV/EBITDA and P/E over 3 and 5 years.
2. Identify the 25th/50th/75th percentile of the historical range.
3. Apply those multiples to current or NTM financials.

### Market-Implied Check

Reverse-engineer the current price. Steps:
1. Set DCF to the current share price and solve for the implied terminal growth rate (holding WACC and forecast constant).
2. Alternatively, compute the revenue CAGR and EBIT margin that would justify the current price at a market-level discount rate.
3. Assess whether the market-implied assumptions are achievable, stretched, or already exceeded.

## Sanity Checks

Run all five sanity checks after producing the reconciliation table. Each check must be documented in `valuation_analysis.md`.

### Sanity Check 1: Historical Multiples

Is the Base implied multiple within a reasonable range of the stock's own historical trading range?
- If the Base DCF implies a multiple above the historical 90th percentile, explain what has structurally changed.
- If the Base DCF implies a multiple below the historical 10th percentile, explain why persistent discount is warranted.

### Sanity Check 2: Peer Premium or Discount

Does the implied Base price represent a premium or discount to trading comps, and is the premium/discount justified?
- Compute the implied premium/discount: (Base DCF price - Comps Base price) / Comps Base price.
- If premium > 25%, require an explicit moat, growth, or quality argument.
- If discount > 25%, require an explicit execution, governance, or structural argument.

### Sanity Check 3: Market-Implied Growth

What growth rate does the current market price imply? Is it above or below the Base case?
- If the market is already pricing in Base case growth, the upside depends entirely on execution above Base — document this.
- If the market is pricing in Bear case or below, document what catalyst would re-rate the stock.

### Sanity Check 4: IRR Check

At the Base case price target with a 12-month horizon, what is the implied IRR?
- Compute: (Base price target + 12-month dividends) / Current price - 1.
- Require IRR to exceed cost of equity (WACC equity component) for a Buy recommendation.
- Document whether the IRR clears the minimum threshold or not.

### Sanity Check 5: Market Cap Reasonableness

Does the implied market cap make intuitive sense in the context of the company's earnings, revenue, and industry?
- At Base price, compute implied market cap, EV, P/E, EV/EBITDA, and EV/Revenue.
- Cross-check against the absolute size of the business: a company with RMB 1bn revenue should not have a Base EV of RMB 50bn without extraordinary margin or growth.
- Flag any implied multiples that would place the company in the top or bottom decile of its sector globally.

## Output

Produce the following files:

### `valuation_analysis.md` under `03_valuation/`

Structure:
1. **Reconciliation Table** — the five-method table with weights.
2. **Weighted Price Target** — Base, Bull, and Bear implied prices, upside/downside from current.
3. **Method Narratives** — one paragraph per method explaining the assumptions used.
4. **Five Sanity Checks** — one section per check with finding and verdict.
5. **Conclusion** — recommended price target, rating rationale, and key assumptions that would change the view.

### `valuation_state.json` under `03_valuation/`

```json
{
  "ticker": "string",
  "as_of_date": "YYYY-MM-DD",
  "current_price": "number",
  "currency": "string",
  "methods": {
    "dcf": { "low": null, "base": null, "high": null, "weight": null },
    "trading_comps": { "low": null, "base": null, "high": null, "weight": null },
    "precedent_transactions": { "low": null, "base": null, "high": null, "weight": null, "applicable": true },
    "historical_multiples": { "low": null, "base": null, "high": null, "weight": null },
    "market_implied_check": { "implied_growth": null, "implied_ebit_margin": null, "weight": 0 }
  },
  "weighted_price_target": { "bear": null, "base": null, "bull": null },
  "upside_downside_pct": null,
  "rating": "Buy | Neutral | Sell | Not Rated",
  "sanity_checks": {
    "historical_multiples": "PASS | WARN | FAIL",
    "peer_premium_discount": "PASS | WARN | FAIL",
    "market_implied_growth": "PASS | WARN | FAIL",
    "irr_check": "PASS | WARN | FAIL",
    "market_cap_reasonableness": "PASS | WARN | FAIL"
  },
  "assumptions_that_would_change_view": ["string"]
}
```
