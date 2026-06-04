---
name: financial-data-normalization
description: Normalize, source, and cross-check historical financial data from iFind MCP for three-statement modeling.
---

# Financial Data Normalization

Use this skill during Task 2 to collect, normalize, and source-check historical financial data for three-statement modeling. The output is `financial_facts.json`, which anchors all downstream assumptions in Task 3. Every number in `financial_facts.json` must be traceable to a source or explicitly flagged `[UNSOURCED]`.

## Step 1: Identify the Reporting Standard

Before collecting any data, determine which accounting standard governs the financial statements:

- **A-share GAAP (Chinese GAAP / ASBEs)**: applies to companies listed on Shanghai or Shenzhen exchanges. Revenue recognition, lease accounting, and financial instrument classification follow Chinese ASBE standards, which may diverge from IFRS in treatment of minority interests, revenue from construction contracts, and government grants.
- **IFRS**: applies to H-share companies (Hong Kong), many Singapore-listed companies, and dual-listed issuers. IFRS 15 (revenue recognition) and IFRS 16 (leases) may produce material differences vs. A-share GAAP.
- **HK GAAP**: largely converged with IFRS, but legacy differences exist for older filings.
- **US GAAP**: applies to US-listed companies and ADRs. ASC 606 (revenue recognition) and ASC 842 (leases) may differ from IFRS.

Document the standard used and flag any year-over-year restatements or standard changes in the collection period.

## Step 2: Collect Historical Data via iFind MCP

Use iFind MCP as the primary data source for A-share and H-share companies. For each company, collect the following data series for the most recent 5 fiscal years (or as many as available):

**Income Statement:**
- Total revenue (and segment revenue if available)
- Cost of revenue / cost of goods sold
- Gross profit and gross margin
- Operating expenses (R&D, SG&A, other operating expenses separately where disclosed)
- EBIT (operating profit before interest and tax)
- EBITDA (compute as EBIT + D&A if not directly available)
- Depreciation and amortization (D&A)
- Interest income and interest expense
- Pre-tax income
- Income tax expense and effective tax rate
- Net income attributable to the parent / controlling shareholders
- Minority interest (non-controlling interest)
- EPS (basic and diluted)

**Balance Sheet:**
- Total assets
- Cash and cash equivalents (and short-term investments if included in cash)
- Accounts receivable and notes receivable
- Inventory
- Other current assets (summarized)
- Total current assets
- PP&E (net), intangible assets, goodwill
- Total non-current assets
- Accounts payable and notes payable
- Short-term debt (including current portion of long-term debt)
- Other current liabilities (summarized)
- Total current liabilities
- Long-term debt
- Total non-current liabilities
- Total equity (including minority interest)
- Retained earnings
- Total liabilities and equity

**Cash Flow Statement:**
- Cash from operations (CFO)
- Net income (reconciliation starting point)
- D&A (as reported in CF statement)
- Changes in working capital: receivables, inventory, payables (separately)
- Other CFO adjustments
- Capital expenditures (CapEx) — cash paid for PP&E and intangibles
- Acquisitions / disposals (net)
- Other cash from investing (CFI total)
- Debt issuance / repayment
- Dividends paid (to parent shareholders and minority)
- Share buybacks / issuances
- Other cash from financing (CFF total)
- Net change in cash

**Share Data:**
- Basic shares outstanding (beginning and end of period, weighted average)
- Diluted shares (weighted average for EPS)
- Share price (closing price at fiscal year end)
- Market capitalization (at fiscal year end)

## Step 3: Normalize Accounting Differences

Apply the following normalization adjustments when comparing across standards or over time:

### IFRS 16 / Lease Accounting

If the company transitioned to IFRS 16 (or equivalent) during the collection period:
- Identify the lease liability and right-of-use asset recognized at transition.
- Adjust pre-transition years: add back lease payments to EBIT (they were above the line as rent), remove from CFO, and reflect in CFI/CFF. This normalizes EBITDA for comparability.
- Flag adjusted years as `[NORMALIZED: IFRS16]`.

### Government Grants (A-share GAAP)

A-share companies often receive government grants recorded as "other income" or "non-operating income." These may be one-time or recurring:
- Separately identify recurring policy subsidies vs. one-time capital grants.
- If material (>5% of EBIT), present both "reported EBIT" and "EBIT excluding government grants."
- Flag as `[NOTE: government_grants]` with the annual amount.

### Non-Recurring Items

Identify and separately document non-recurring items that distort trend analysis:
- Asset impairments or write-downs
- Gains/losses on disposal of subsidiaries or assets
- Litigation settlements
- Restructuring charges
- Fair value changes on financial instruments (if flow through P&L)

Present both reported and adjusted figures where material.

### Revenue Recognition Differences

For companies where revenue recognition changed (e.g., gross-to-net, milestone-to-ratable, or adoption of ASBE 14 in China):
- Identify the transition year and the magnitude of the change.
- Restate prior years on a pro-forma basis if disclosed. If not, flag the break in the series.

### Currency

If the company reports in a currency different from the analytical currency:
- Use the average exchange rate for income statement items and the period-end rate for balance sheet items.
- Document the exchange rates used.

## Step 4: Compute Derived Metrics

After collecting raw data, compute the following derived metrics and include them in `financial_facts.json`:

- **Gross margin %**: gross profit / revenue
- **EBIT margin %**: EBIT / revenue
- **EBITDA margin %**: EBITDA / revenue
- **Net margin %**: net income (attributable to parent) / revenue
- **Revenue growth YoY %**
- **FCF**: CFO - CapEx
- **FCF conversion**: FCF / net income
- **NWC**: (accounts receivable + inventory) - accounts payable (use consistent definition across years)
- **NWC/Revenue %**
- **CapEx/Revenue %**
- **D&A/Revenue %**
- **Receivables days (DSO)**: accounts receivable / (revenue / 365)
- **Inventory days (DIO)**: inventory / (COGS / 365)
- **Payables days (DPO)**: accounts payable / (COGS / 365)
- **Net debt**: total debt - cash
- **Net debt / EBITDA**: leverage ratio
- **Interest coverage**: EBIT / interest expense
- **Return on equity (ROE)**: net income / average equity
- **Return on invested capital (ROIC)**: NOPAT / average invested capital

## Step 5: Cross-Check and Source Verification

Run the following cross-checks before finalizing `financial_facts.json`:

- **Balance sheet check**: total assets = total liabilities + equity for each year.
- **Cash tie-out**: ending cash on balance sheet = prior year cash + net change in cash from CF statement.
- **Net income link**: net income on CF statement = net income on IS (before minority interest adjustment if applicable).
- **D&A consistency**: D&A on CF statement reconciles to D&A on IS and PP&E schedule.
- **CapEx/PP&E tie**: CapEx on CF statement is consistent with the movement in PP&E net of D&A.

Flag any discrepancy with `[RECONCILIATION_GAP: description]`.

For each data point, record the source. Acceptable sources:
- iFind MCP (specify the query or field)
- Company annual report (specify year and page)
- Company interim report
- Exchange filing (specify filing date)
- Management guidance or earnings call transcript
- Peer or industry data used as proxy (must be explicitly noted)

Any item without a verifiable source must be flagged `[UNSOURCED: description]`.

## Output

Produce `financial_facts.json` under `02_financial_model/` with the following schema:

```json
{
  "ticker": "string",
  "company": "string",
  "market": "string",
  "currency": "string",
  "reporting_standard": "A-share GAAP | IFRS | HK GAAP | US GAAP",
  "fiscal_year_end": "string",
  "normalization_notes": ["string"],
  "years": ["YYYY"],
  "income_statement": {
    "revenue": ["number"],
    "revenue_by_segment": {
      "segment_name": ["number"]
    },
    "gross_profit": ["number"],
    "ebit": ["number"],
    "ebitda": ["number"],
    "da": ["number"],
    "net_income_parent": ["number"],
    "eps_basic": ["number"],
    "eps_diluted": ["number"],
    "effective_tax_rate": ["number"],
    "non_recurring_items": {
      "description": ["number"]
    }
  },
  "balance_sheet": {
    "cash": ["number"],
    "accounts_receivable": ["number"],
    "inventory": ["number"],
    "total_current_assets": ["number"],
    "ppe_net": ["number"],
    "total_assets": ["number"],
    "accounts_payable": ["number"],
    "short_term_debt": ["number"],
    "long_term_debt": ["number"],
    "total_debt": ["number"],
    "total_equity": ["number"],
    "retained_earnings": ["number"]
  },
  "cash_flow": {
    "cfo": ["number"],
    "capex": ["number"],
    "fcf": ["number"],
    "dividends_paid": ["number"],
    "net_change_in_cash": ["number"]
  },
  "share_data": {
    "shares_basic_wtd_avg": ["number"],
    "shares_diluted_wtd_avg": ["number"],
    "shares_outstanding_eop": ["number"],
    "price_eop": ["number"],
    "market_cap_eop": ["number"]
  },
  "derived_metrics": {
    "gross_margin_pct": ["number"],
    "ebit_margin_pct": ["number"],
    "ebitda_margin_pct": ["number"],
    "net_margin_pct": ["number"],
    "revenue_growth_yoy_pct": ["number"],
    "fcf_conversion_pct": ["number"],
    "nwc": ["number"],
    "nwc_pct_revenue": ["number"],
    "capex_pct_revenue": ["number"],
    "da_pct_revenue": ["number"],
    "dso_days": ["number"],
    "dio_days": ["number"],
    "dpo_days": ["number"],
    "net_debt": ["number"],
    "net_debt_to_ebitda": ["number"],
    "interest_coverage": ["number"],
    "roe_pct": ["number"],
    "roic_pct": ["number"]
  },
  "model_projection_summary": {
    "projection_years": ["YYYY"],
    "projected_revenue_growth_pct": {
      "bear": ["number"],
      "base": ["number"],
      "bull": ["number"]
    },
    "projected_ebit_margin_pct": {
      "bear": ["number"],
      "base": ["number"],
      "bull": ["number"]
    }
  },
  "sources": [
    {
      "field": "string",
      "source": "string",
      "date": "YYYY-MM-DD"
    }
  ],
  "unsourced_items": ["string"],
  "reconciliation_gaps": ["string"]
}
```

**Array ordering**: all arrays are ordered chronologically, oldest to most recent. The `years` array defines the order for all income statement, balance sheet, cash flow, and share data arrays.

## Quality Gate

Before passing `financial_facts.json` to Task 3, verify:

- At least 3 years of revenue and EBIT data are present with no `[UNSOURCED]` flag on those fields.
- All balance sheet checks pass (assets = liabilities + equity for every year).
- All cash tie-out checks pass.
- D&A and CapEx are present for at least 3 years.
- NWC (receivables + inventory - payables) is present and shows a consistent definition across years.
- `unsourced_items` list is explicitly populated (empty array if none).
