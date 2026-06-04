---
name: three-statement-model
description: Build the Task 2 integrated three-statement workbook for single-stock coverage with linked IS, BS, CF, schedules, checks, and DCF inputs.
---

# Three-Statement Model

Use this skill to create `02_financial_model/integrated_model.xlsx`. This is an integrated forecast model, not a financial-data extraction sheet.

## Required Workbook Tabs

The workbook must include these tabs in this order unless a user-provided template requires a documented exception:

1. `Cover`
2. `Sources`
3. `Assumptions`
4. `Revenue Build`
5. `Income Statement`
6. `Balance Sheet`
7. `Cash Flow Statement`
8. `Working Capital`
9. `PP&E & D&A`
10. `Debt & Interest`
11. `Share Count`
12. `DCF Inputs`
13. `Checks`

## Formula-First Rule

- Every projection cell must be an Excel formula.
- Every subtotal, roll-forward, cross-statement linkage, and check must be an Excel formula.
- Only historical actuals and assumption drivers may be hardcoded.
- Every hardcoded input must have a source on `Sources` or an `[UNSOURCED]` marker.
- When generating with Python/openpyxl, write formula strings such as `=D14*(1+Assumptions!D8)`, not Python-computed values.

## Tab Requirements

### Cover

- Company, ticker, exchange, currency, unit, fiscal year end, model date, authoring run ID.
- Output inventory and audit status.

### Sources

- Source ID, document name, publication date, accessed date, URL or database string, line items supported, notes.
- Link hardcoded historical and assumption inputs back to source IDs.

### Assumptions

- Forecast period labels and scenario selector if scenarios are used.
- Revenue drivers from Task 1: price, volume, segment growth, customer, geography, utilization, ARPU, or other relevant variables.
- Margin, tax, working-capital, D&A, CapEx, debt, interest, dividend, buyback, and share-count assumptions.
- Scenario assumptions for Bear/Base/Bull where available.

### Revenue Build

- Segment, product, geography, or driver-level revenue build based on Task 1 business driver map.
- Total revenue must sum from the build and link into `Income Statement`.
- Include growth and mix metrics as formulas.

### Income Statement

- Revenue linked from `Revenue Build`.
- COGS, gross profit, operating expenses, EBITDA, D&A, EBIT, interest expense, pre-tax income, tax, net income, and EPS where relevant.
- Net income must link to the retained earnings roll-forward and cash flow statement.

### Balance Sheet

- Cash, working-capital accounts, PP&E, other assets, debt, other liabilities, retained earnings, total equity, total assets, total liabilities plus equity.
- Historical values may be hardcoded with source references; projections must link to schedules and assumptions.

### Cash Flow Statement

- Net income linked from `Income Statement`.
- D&A linked from `PP&E & D&A`.
- Working-capital changes linked from `Working Capital`.
- CapEx linked from `PP&E & D&A`.
- Debt issuance/repayment linked from `Debt & Interest`.
- Buybacks/dividends linked from `Share Count` or `Assumptions`.
- Ending cash must tie to `Balance Sheet` cash.

### Working Capital

- AR, inventory, AP, accrued liabilities, deferred revenue, or company-relevant working-capital accounts.
- Use days, percentage of revenue/COGS, or other explicit drivers.
- Working-capital changes must flow to `Cash Flow Statement` with the correct sign convention.

### PP&E & D&A

- Beginning PP&E, CapEx, acquisitions/disposals where material, D&A, ending PP&E.
- D&A must link to `Income Statement` and `Cash Flow Statement`.
- CapEx must link to `Cash Flow Statement`.
- Ending PP&E must link to `Balance Sheet`.

### Debt & Interest

- Beginning debt, issuance, repayment, amortization, ending debt, average debt, interest rate, interest expense.
- Interest expense must link to `Income Statement`.
- Debt issuance/repayment must link to `Cash Flow Statement`.
- Ending debt must link to `Balance Sheet`.

### Share Count

- Basic and diluted shares, buybacks, issuance, options/convertibles if material.
- Diluted shares must support EPS and Task 3 per-share valuation.

### DCF Inputs

This tab is the handoff to Task 3. It must pull from the model, not duplicate hardcoded outputs:

- Revenue from `Revenue Build`.
- EBIT and tax from `Income Statement`.
- D&A from `PP&E & D&A`.
- CapEx from `Cash Flow Statement` or `PP&E & D&A`.
- NWC change from `Working Capital`.
- Debt and cash from `Balance Sheet`.
- Shares from `Share Count`.
- Scenario outputs and projection summary where available.

### Checks

Include a visible dashboard with formula-based checks for every historical and projected period:

- `BS balance`: Total Assets = Total Liabilities + Equity.
- `Cash tie-out`: Cash Flow Statement ending cash = Balance Sheet cash.
- `NI link`: Income Statement net income = Cash Flow Statement net income = retained earnings input.
- `RE roll-forward`: Prior retained earnings + net income - dividends = ending retained earnings.
- `CapEx/PP&E tie`: Beginning PP&E + CapEx - D&A +/- acquisitions/disposals = ending PP&E, and ending PP&E ties to Balance Sheet.
- `Debt tie`: Beginning debt + issuance - repayment/amortization = ending debt, and ending debt ties to Balance Sheet.
- `Revenue tie`: Revenue Build total = Income Statement revenue.
- `D&A tie`: PP&E & D&A schedule D&A = Income Statement and Cash Flow Statement D&A.

Critical checks must return an explicit `TRUE/FALSE` or zero-difference result.

## Build Sequence

1. Create the tab structure and period headers.
2. Load normalized historical facts and source references.
3. Populate historical actuals and assumption drivers as blue-font inputs.
4. Build revenue and operating forecasts from Task 1 drivers.
5. Build supporting schedules before projected financial statements.
6. Link Income Statement, Balance Sheet, and Cash Flow Statement.
7. Populate `DCF Inputs` from linked model outputs.
8. Add `Checks` formulas and named ranges for key outputs.
9. Save as `02_financial_model/integrated_model.xlsx`.

## Acceptance Criteria

- All required tabs exist and are populated.
- Projection cells, subtotals, roll-forwards, and checks are formulas.
- BS balances in every period.
- Cash ties out in every period.
- NI link, RE roll-forward, CapEx/PP&E tie, and debt tie pass or are clearly marked as unresolved Critical audit issues.
- `DCF Inputs` is complete enough for Task 3 to build DCF scenarios without re-normalizing historical financials.
