---
name: statement-reconciliation-checks
description: Reconcile independent IS, BS, and CF JSON specs before building Task 2 workbook.
---

# Statement Reconciliation Checks

Use this skill only on `task2_financial_modeler`.

## Inputs

- `02_financial_model/income_statement_spec.json`
- `02_financial_model/balance_sheet_spec.json`
- `02_financial_model/cash_flow_statement_spec.json`

## Required Checks

Before workbook build, reconcile the independent statement JSON artifacts:

- Income Statement `net_income` must be declared as the Cash Flow Statement `net_income_cf` dependency.
- Cash Flow Statement `ending_cash` must be declared as the Balance Sheet `cash_and_equivalents` dependency.
- Balance Sheet `retained_earnings` must declare net income and dividends dependencies.
- DCF input dependencies must exist for revenue, EBIT, tax, D&A, CapEx, NWC change, debt, cash, and diluted shares.
- Every statement must carry source coverage and `[UNSOURCED]` lists forward.
- Forecast hardcode risk must be flagged before workbook build.

## Severity

- Critical: missing statement JSON, missing canonical key, failed cross-statement dependency, invalid source coverage, or DCF input dependency gap.
- Warning: `[UNSOURCED]` facts, weak assumption support, formula dependency gaps, or hardcode risk.

Critical findings block assignment to `workbook_builder`. Warnings may pass only if documented in `model_audit.md`.

## Output

Write `02_financial_model/statement_spec_pack.json` with:

- `status`
- `statement_specs`
- `critical`
- `warnings`
- `builder_blocked`

