---
name: company-research
description: Research a company's business model, drivers, competitive position, risks, and catalysts for single-stock coverage Task 1.
---

# Company Research

Use this skill to complete Task 1 of the single-stock coverage workflow. The goal is to establish a thorough factual foundation that all downstream tasks (financial modeling, valuation, report assembly) will depend on. Do not skip or abbreviate sections — incomplete research here cascades into unsupported assumptions in Task 3.

## Scope

Task 1 answers: how does this company make money, what variables drive future value, and what facts would invalidate the current investment thesis?

## Step 1: Company Identity

Establish the following fields precisely before proceeding:

- Full legal name, ticker, exchange, and market (e.g., A-share / H-share / ADR).
- Reporting currency and functional currency if different.
- Fiscal year end and reporting calendar (quarterly / semi-annual / annual).
- Listing status: primary, dual-listed, or GDR.
- Controlling shareholder and ownership structure (state-owned, private, family, foreign).
- Index membership (CSI 300, MSCI, Hang Seng, etc.) and any pending inclusion/exclusion.

## Step 2: Business Model Analysis

Map the economic engine of the business:

- **Products and services**: describe each major product or service line, its revenue contribution, and gross margin profile.
- **Revenue recognition**: identify whether revenue is recognized at point of sale, over time, or by milestone. Flag deferred revenue, contract liabilities, or bill-and-hold practices.
- **Pricing and volume**: decompose revenue into price and volume components. Identify ASP trends, volume trends, and whether pricing is market-set or contract-set.
- **Customer concentration**: name the top customers if disclosed. Flag if top-3 customers exceed 30% of revenue.
- **Geographic and channel mix**: break down revenue by geography and sales channel. Identify where growth is coming from.
- **Cost structure**: separate fixed vs. variable costs. Identify the largest cost lines and whether they are input-price sensitive.

## Step 3: Management and Governance

- Management team background: relevant industry experience, tenure, track record on guidance accuracy.
- Incentive structure: how are executives compensated? Is compensation tied to revenue, profit, or share price?
- Ownership: does management own shares? Are there recent insider buys or sells?
- Governance flags: related-party transactions, audit committee independence, auditor history (changes, qualifications), VIE structures if applicable.
- Capital allocation history: how has free cash flow been deployed (reinvestment, M&A, dividends, buybacks)?

## Step 4: Competitive Landscape

- Direct competitors: list the top 3-5 by revenue or market share. Describe how this company differs on price, product, or service.
- Market share: is the company gaining or losing share? What does channel data or industry reports suggest?
- Moat assessment: identify and rate network effects, switching costs, cost advantages, intangible assets, and scale.
- Substitute products or technologies: are there credible substitutes gaining traction?
- Barriers to entry: capital intensity, regulatory approval, IP, distribution, brand.

## Step 5: Industry and Policy Impact on the Stock

This section absorbs sector and thematic context only insofar as it directly affects this ticker. Do not reproduce generic industry commentary.

- What specific regulatory changes affect this company's pricing, volume, or cost?
- What macro or commodity inputs are most relevant to margins?
- If sector policy is supplied by the outer agent, extract the specific sub-items that are company-relevant and translate them into potential financial impact (e.g., "policy cap on ASP reduces revenue by X% under bear case").
- Identify whether the company is a policy beneficiary, neutral, or at risk.

## Step 6: Risk Inventory

Document risks under six categories. For each risk, describe the mechanism (how it flows through financials) and rate severity (High / Medium / Low):

1. **Fundamental risks**: demand decline, product obsolescence, technology disruption, customer loss.
2. **Financial quality risks**: aggressive revenue recognition, channel stuffing, receivables stretch, weak cash conversion, off-balance-sheet liabilities.
3. **Governance risks**: related-party transactions, controlling shareholder expropriation, management misconduct history.
4. **Regulatory and legal risks**: pending investigations, license renewal, antitrust, environmental compliance, cross-border sanctions.
5. **Liquidity risks**: free float size, average daily trading volume, lock-up expiry, block sale risk.
6. **Valuation risks**: crowded trade, mean reversion, premium that requires sustained execution.

## Step 7: Catalyst Map

Identify near-term and medium-term catalysts under the following categories. For each catalyst, specify the direction of impact (positive / negative / binary), likely timing, and magnitude (material / moderate / minor):

- **Earnings and guidance**: results dates, pre-announcement windows, consensus revision potential.
- **Policy events**: regulatory decisions, subsidy announcements, tariff changes.
- **Price and cost catalysts**: upstream commodity shifts, ASP changes, contract renewals.
- **Orders and backlog**: major contract wins, RFQ outcomes, order book disclosures.
- **Capacity and production**: new facility ramp, expansion milestones, production disruption.
- **Capital return**: buyback programs, special dividends, dividend initiation.
- **Shareholder reduction**: major shareholder lock-up expiry, block sale, pledge release risk.
- **Index events**: inclusion in or exclusion from major indices, Hong Kong Stock Connect eligibility changes.

## Output

Produce the following files under `01_company_research/`:

### `company_research.md`

A structured research document covering Steps 1-7 above. Each section should be clearly labeled. Flag any data gaps as `[UNSOURCED: description]` inline.

### `business_driver_map.json`

Translate the business facts into model-relevant variables. Use the following schema:

```json
{
  "ticker": "string",
  "company": "string",
  "as_of_date": "YYYY-MM-DD",
  "revenue_drivers": [
    {
      "driver": "string",
      "description": "string",
      "segments": ["string"],
      "bear_direction": "string",
      "base_direction": "string",
      "bull_direction": "string",
      "evidence": "string"
    }
  ],
  "margin_drivers": [
    {
      "driver": "string",
      "description": "string",
      "bear_impact": "string",
      "base_impact": "string",
      "bull_impact": "string",
      "evidence": "string"
    }
  ],
  "capex_drivers": [
    {
      "driver": "string",
      "description": "string",
      "maintenance_vs_growth": "maintenance | growth | both",
      "evidence": "string"
    }
  ],
  "working_capital_drivers": [
    {
      "driver": "string",
      "description": "string",
      "receivables_days": "number or null",
      "inventory_days": "number or null",
      "payables_days": "number or null",
      "evidence": "string"
    }
  ],
  "risk_drivers": [
    {
      "risk": "string",
      "category": "fundamental | financial_quality | governance | regulatory | liquidity | valuation",
      "severity": "High | Medium | Low",
      "financial_mechanism": "string",
      "evidence": "string"
    }
  ],
  "catalyst_drivers": [
    {
      "catalyst": "string",
      "category": "earnings | policy | price | orders | capacity | buyback | reduction | index",
      "direction": "positive | negative | binary",
      "timing": "string",
      "magnitude": "material | moderate | minor",
      "evidence": "string"
    }
  ],
  "unsourced_items": ["string"]
}
```

### `source_log.json`

A list of all sources consulted, with the following schema per entry:

```json
[
  {
    "source_id": "string",
    "type": "company_filing | broker_report | news | regulatory | ifind | management_call | other",
    "title": "string",
    "date": "YYYY-MM-DD",
    "url_or_reference": "string",
    "used_in": ["string"]
  }
]
```

## Quality Gate

Before passing artifacts to Task 2, verify:

- `business_driver_map.json` has at least one entry in each of the six driver categories.
- All high-severity risks have a documented financial mechanism.
- All catalysts have a timing estimate.
- `[UNSOURCED]` items are explicitly listed in `unsourced_items` array.
- Sources in `source_log.json` cover all material claims in `company_research.md`.
