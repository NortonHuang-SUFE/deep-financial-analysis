---
name: dcf-assumption-generation
description: Generate Bear/Base/Bull scenario DCF assumptions grounded in business driver map and financial facts.
---

# DCF Assumption Generation

Use this skill to complete Task 3 Steps 3.1-3.3 of the single-stock coverage workflow: run the Evidence Gate, build the Value Driver Map, and produce Bear/Base/Bull assumptions for all DCF inputs. The output feeds directly into `assumption-audit` (Step 3.4) and then `dcf-builder` execution (Step 3.5).

The central goal is not to produce a number — it is to answer three questions about every assumption:
1. Is there sufficient information to make this assumption?
2. Is the assumption internally logical?
3. Can the assumption be proven wrong by observable data?

## Step 3.1: Evidence Gate

Before generating any assumptions, verify that Task 1 and Task 2 have produced the required foundation.

**Required inputs:**
- `01_company_research/business_driver_map.json` — must have entries in all six driver categories (revenue, margin, capex, working_capital, risk, catalyst).
- `01_company_research/source_log.json` — must show sourced evidence for all material claims.
- `02_financial_model/financial_facts.json` — must contain at least 3 years of historical revenue, EBIT, EBITDA, D&A, CapEx, NWC change, debt, cash, and shares.
- `02_financial_model/integrated_model.xlsx` — must have passed `audit-xls`.

**Evidence Gate checks:**
- Are there any `[UNSOURCED]` items in `business_driver_map.json` that affect revenue or margin assumptions? If yes, document them in `evidence_sufficiency.md` and either resolve or accept with justification.
- Are there data gaps in historical financials covering more than one year? If yes, flag and use peer data or disclosed guidance as proxy.
- Is there management guidance available for the next 1-2 years? If yes, note guidance accuracy history before relying on it.

**Output:** `evidence_sufficiency.md` documenting what is known, what is missing, and how gaps will be handled.

**Gate rule:** Do not proceed to Step 3.2 if revenue drivers and margin drivers in `business_driver_map.json` are both empty or entirely `[UNSOURCED]`.

## Step 3.2: Value Driver Map

Translate the qualitative business driver map into quantified financial forecast levers. This step bridges business research and model assumptions.

For each driver category in `business_driver_map.json`, specify:

**Revenue drivers:**
- Which segments or products exist, and what is each segment's share of total revenue?
- For each segment: what determines volume growth (capacity, demand, market share, product cycle)?
- For each segment: what determines price (contract terms, market pricing, ASP trend, policy cap)?
- What is the segment revenue growth range that corresponds to Bear/Base/Bull outcomes?

**Margin drivers:**
- What is the company's fixed vs. variable cost structure? What is the operating leverage coefficient?
- What cost lines are input-price sensitive, and what is the relevant commodity or input index?
- What efficiency improvements or cost headwinds are expected over the forecast period?
- How do margins behave under each scenario: does revenue decline cause disproportionate margin compression?

**CapEx drivers:**
- What is the split between maintenance CapEx and growth CapEx?
- What capacity expansion is planned, and what revenue growth does it enable?
- What is the asset intensity: CapEx/revenue or CapEx/EBITDA vs. peers and history?

**Working capital drivers:**
- What are the company's receivables days, inventory days, and payables days over the last 3 years?
- Are commercial terms changing (e.g., customer mix shift, advance payment requirements)?
- How does NWC behave in a revenue growth vs. revenue decline scenario?

**WACC inputs:**
- Current market cap and market value of debt.
- Cost of equity components: risk-free rate (long-term government bond in reporting currency), equity risk premium (country/market-specific), beta (observed or peer-estimated).
- Cost of debt: yield-to-maturity on outstanding bonds or marginal borrowing rate.
- Target or current capital structure in market value terms.

**Terminal value inputs:**
- Long-run nominal GDP growth in the primary market.
- Industry maturity and structural growth trajectory.
- Reinvestment rate required to sustain terminal growth.

**Output:** `value_driver_map.json` with the following schema:

```json
{
  "ticker": "string",
  "as_of_date": "YYYY-MM-DD",
  "forecast_period_years": "number",
  "segments": [
    {
      "name": "string",
      "revenue_share_pct": "number",
      "volume_driver": "string",
      "price_driver": "string",
      "evidence": "string"
    }
  ],
  "revenue_levers": {
    "bear": "string",
    "base": "string",
    "bull": "string"
  },
  "margin_levers": {
    "fixed_cost_pct_revenue": "number or null",
    "operating_leverage_note": "string",
    "bear": "string",
    "base": "string",
    "bull": "string"
  },
  "capex_levers": {
    "maintenance_capex_pct_revenue": "number or null",
    "growth_capex_driver": "string",
    "evidence": "string"
  },
  "nwc_levers": {
    "receivables_days_history": "number or null",
    "inventory_days_history": "number or null",
    "payables_days_history": "number or null",
    "nwc_trend": "string"
  },
  "wacc_inputs": {
    "risk_free_rate": "number or null",
    "equity_risk_premium": "number or null",
    "beta": "number or null",
    "cost_of_debt": "number or null",
    "tax_rate": "number or null",
    "equity_weight_market_value": "number or null",
    "debt_weight_market_value": "number or null"
  },
  "terminal_growth_rationale": "string"
}
```

## Step 3.3: Assumption Generation

Using the evidence from Steps 3.1-3.2, generate Bear/Base/Bull assumptions for all DCF inputs.

**For each scenario, produce assumptions for the following variables:**

### Revenue Growth (per forecast year, by segment then aggregated)

- **Bear**: Identify the adverse case. What goes wrong — demand falls, prices decline, market share is lost, or a regulatory cap bites? The Bear case must reflect at least one mechanism from `risk_drivers` in `business_driver_map.json`. The gap between Bear and Base cumulative revenue should be at least 5 percentage points over the forecast period.
- **Base**: The operationally plausible case grounded in observable milestones. Cross-check against: (a) historical 3-year average growth, (b) management guidance, (c) capacity or order book data. Do not use consensus as the base without scrutiny. Base is not the midpoint of Bear and Bull.
- **Bull**: The upside case with a specific catalyst. What drives outperformance — new capacity online, product cycle, share gain, ASP recovery, or policy tailwind? Bull must be tied to at least one `catalyst_drivers` entry in `business_driver_map.json`.

### EBIT Margin (per forecast year)

- Anchor to the company's last 5 years of EBIT margin history and peer median range.
- Bear: reflect cost deleveraging from lower revenue. Margin compression should be proportionate to fixed cost exposure.
- Base: continuation of current trend or evidence-supported improvement. Explain the source of any improvement (scale, mix, cost reduction).
- Bull: expansion scenario with explicit evidence (pricing power, mix improvement, cost program).

### CapEx / Revenue

- Separate maintenance CapEx (non-negotiable floor) from growth CapEx (linked to revenue growth scenario).
- Bear: base or slightly above base CapEx/revenue (maintenance cannot be cut significantly).
- Base: consistent with historical average and disclosed capital programs.
- Bull: potentially higher in absolute terms but lower as a ratio due to scale leverage.

### NWC / Revenue Delta

- Derive from receivables days, inventory days, and payables days assumptions.
- Verify the NWC calculation method used in `integrated_model.xlsx` for consistency.
- Bear: NWC may worsen (customers stretch payables, inventory builds).
- Base: stable working capital cycle, gradual normalization.
- Bull: improvement from better commercial terms or faster collections.

### WACC

- Use a single WACC for all three scenarios (reflect through scenario sensitivity, not scenario-specific WACC).
- Document every input: risk-free rate, ERP, beta, cost of debt, tax rate, capital structure weights.
- All weights must use market values. Flag if market cap is highly volatile and a trailing average is used.

### Terminal Growth Rate

- Must be strictly below WACC (verify mathematically).
- Must not equal near-term projected growth rates.
- Set relative to long-run nominal GDP growth in the primary market, adjusted for industry maturity.
- Document the rationale explicitly.

**Assumption Generation Principles:**
- Every non-trivial assumption must cite a source: historical data, peer data, management guidance, or industry data.
- Mark any assumption without a source as `[UNSOURCED: description]`.
- Do not force symmetry: Bear and Bull do not need to be equidistant from Base.
- Prefer tables and structured bullets over prose for the final assumption output.

## Output

Produce the following files under `03_valuation/`:

### `evidence_sufficiency.md`

Document the Evidence Gate outcome:
- Data available and sufficient.
- Data gaps and how they are handled.
- `[UNSOURCED]` items carried forward.
- Gate verdict: PROCEED | PROCEED WITH CONDITIONS | BLOCKED.

### `value_driver_map.json`

Per schema above in Step 3.2.

### `assumption_pack.md`

Structure the assumption pack as follows:

```markdown
## 1. Valuation Conclusion (placeholder — filled after Steps 3.4-3.6)
## 2. Information Foundation and Gaps
## 3. Value Driver Tree
## 4. Bear/Base/Bull Assumptions
### 4.1 Revenue Growth by Segment and Year
### 4.2 EBIT Margin
### 4.3 CapEx / Revenue
### 4.4 NWC / Revenue Delta
### 4.5 WACC
### 4.6 Terminal Growth Rate
## 5. Assumption Logic
## 6. Assumption Audit (filled by assumption-audit skill)
## 7. DCF Output (filled after model execution)
## 8. Valuation Method Cross-Validation (filled by valuation-reconciliation skill)
## 9. Falsifiable Indicators and Follow-Up Tracking
```

For section 9, list specific observable data points that would cause each key assumption to be revised. For example: "If the company's Q2 utilization rate falls below 70%, the Base revenue growth assumption of X% is no longer supportable."

## Handoff

After producing `evidence_sufficiency.md`, `value_driver_map.json`, and `assumption_pack.md` (sections 2-5 and 9), hand off to `assumption-audit` to complete sections 6. Do not proceed to model execution until `assumption_audit.md` shows no FAIL items on Items 1, 8, and 9 of the audit checklist.
