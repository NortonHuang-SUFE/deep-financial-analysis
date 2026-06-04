---
name: financial-data-normalization
description: Normalize sourced public-company financial data for Task 2 single-stock coverage models before building the integrated three-statement workbook.
---

# Financial Data Normalization

Use this skill after Task 1 research and before building the three-statement workbook. The goal is a sourced, normalized fact base that can support formulas, model checks, and Task 3 DCF inputs.

## Inputs

- `01_company_research/company_research.md`
- `01_company_research/business_driver_map.json`
- `01_company_research/source_log.json`
- Company filings, earnings releases, transcripts, market data, consensus or management guidance when available.
- Any existing model or prior `financial_facts.json` for updates.

## Required Normalization

Create a consistent data set for:

- Company identity: legal name, ticker, exchange, currency, fiscal year end, reporting unit, fiscal period labels.
- Historical income statement: revenue, gross profit, EBIT, EBITDA, pre-tax income, tax, net income, EPS where available.
- Historical cash flow: D&A, stock-based compensation where relevant, CapEx, acquisitions/divestitures, dividends, buybacks, NWC change.
- Historical balance sheet: cash, short-term investments, debt, lease liabilities where material, working-capital accounts, PP&E, retained earnings, total equity.
- Share count: basic shares, diluted shares, buybacks, issuance, dilution drivers.
- Segment detail: segment revenue, volume, price, margin, geography, product lines, or other business drivers from Task 1 when available.

## Cleaning Rules

- Align all periods to the company's fiscal calendar.
- Convert all figures to the workbook reporting currency and unit.
- Preserve original source units and restatement notes in the `Sources` tab or `financial_facts.json`.
- Normalize sign conventions before modeling:
  - Revenue, profit, assets, liabilities, equity, debt, cash, and shares are positive values.
  - Cash outflows such as CapEx, dividends, and buybacks should follow the workbook convention consistently.
  - NWC change must be explicitly defined as either source statement change or operating cash flow adjustment.
- Separate GAAP/IFRS reported values from adjusted values. Do not mix them without a labeled bridge.
- Mark every missing, estimated, or manually inferred value as `[UNSOURCED]` unless a source string supports it.

## Spreadsheet Data Hygiene

When cleaning spreadsheet inputs, follow the same discipline as `clean-data-xls`:

- Profile columns for dominant type and outliers.
- Trim whitespace, standardize period labels, convert numbers stored as text, and flag mixed units.
- Prefer formula-based helper columns for transparent transformations.
- Do not destructively overwrite raw imported data unless explicitly requested.

## Output: financial_facts.json

`financial_facts.json` must be valid JSON and include at minimum:

```json
{
  "company": "",
  "ticker": "",
  "currency": "",
  "unit": "",
  "fiscal_year_end": "",
  "historicals": [],
  "segments": [],
  "guidance": [],
  "projection_summary": {},
  "sources": [],
  "unsourced": []
}
```

Each historical record should include:

- Period label and actual/estimate flag.
- Revenue, EBIT, EBITDA, net income.
- D&A, CapEx, NWC change.
- Debt, cash, diluted shares.
- Segment revenue and margin if available.
- Source string or `[UNSOURCED]`.

## Quality Gate

Before moving to the three-statement model:

- Confirm historical revenue, EBIT, EBITDA, net income, D&A, CapEx, NWC change, debt, cash, and shares are either sourced or explicitly listed as `[UNSOURCED]`.
- Confirm fiscal periods, currency, units, and sign conventions are consistent.
- Confirm Task 1 business drivers are mapped to model variables or documented as unavailable.
