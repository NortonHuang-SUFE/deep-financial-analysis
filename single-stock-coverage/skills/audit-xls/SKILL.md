---
name: audit-xls
description: Mandatory audit procedure for every Excel artifact produced or updated by Task 2 single-stock coverage financial modeling.
---

# Audit XLS

All Excel artifacts produced or updated by Task 2 require an `audit-xls` review before delivery. This is mandatory for `integrated_model.xlsx` and any auxiliary workbook created during financial modeling.

## Required Scope

Use model scope for integrated financial models. Do not treat Task 2 audit as a quick formula scan.

The audit must cover:

- Workbook structure and required tabs.
- Formula integrity.
- Hardcoded values in projection or calculation areas.
- Cross-sheet links.
- Hidden rows, hidden columns, hidden tabs, and stale external links.
- Units, signs, fiscal periods, and source references.
- Financial-model integrity checks.

## Formula-Level Checks

Check every Excel artifact for:

- Formula errors: `#REF!`, `#VALUE!`, `#N/A`, `#DIV/0!`, `#NAME?`, `#NUM!`.
- Hardcodes embedded in formulas where assumptions should be cell references.
- Projection cells that are static values instead of formulas.
- Inconsistent formulas across rows or periods.
- Off-by-one ranges in `SUM`, `AVERAGE`, or subtotal formulas.
- Broken cross-sheet links.
- Circular references, intentional or accidental.
- Unit mismatches and percentage formatting mistakes.

## Task 2 Model Checks

For `integrated_model.xlsx`, verify every historical and projected period:

- BS balance: Total Assets = Total Liabilities + Equity.
- Cash tie-out: Cash Flow Statement ending cash = Balance Sheet cash.
- NI link: Income Statement net income = Cash Flow Statement net income = retained earnings input.
- RE roll-forward: Prior retained earnings + net income - dividends = ending retained earnings.
- CapEx/PP&E tie: Beginning PP&E + CapEx - D&A +/- acquisitions/disposals = ending PP&E, and ending PP&E ties to Balance Sheet.
- Debt tie: Beginning debt + issuance - repayment/amortization = ending debt, and ending debt ties to Balance Sheet.
- Revenue tie: Revenue Build total = Income Statement revenue.
- D&A tie: PP&E & D&A schedule D&A = Income Statement and Cash Flow Statement D&A.
- DCF Inputs tie: DCF Inputs tab pulls from the model, not hardcoded duplicates.

## Severity

- Critical: BS imbalance, cash tie-out failure, broken formulas, missing required tab, DCF Inputs not linked, or unsupported hardcoded projections.
- Warning: inconsistent formulas, risky hardcoded assumptions, weak source traceability, unusual growth/margin logic, unresolved `[UNSOURCED]` assumptions.
- Info: formatting, naming, layout, and documentation improvements.

## Report Format

Write audit findings into `02_financial_model/model_audit.md`:

```markdown
# Model Audit

Model type: integrated 3-statement
Workbook: 02_financial_model/integrated_model.xlsx
Overall: Clean / Minor Issues / Major Issues

| # | Sheet | Cell/Range | Severity | Category | Issue | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|
```

Include:

- Summary of required checks and pass/fail status.
- Count of Critical, Warning, and Info findings.
- Any unresolved issues and whether they block Task 3.
- Notes on `[UNSOURCED]` data that affect model reliability.

## Delivery Gate

Do not deliver a clean Task 2 handoff if Critical findings remain unresolved. If a Critical item cannot be fixed with available information, state that Task 3 should treat the model as blocked or caveated.
