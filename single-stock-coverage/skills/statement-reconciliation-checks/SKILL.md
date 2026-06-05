---
name: statement-reconciliation-checks
description: Reconcile independent IS, BS, and CF JSON specs before building Task 2 workbook.
---

# Statement Reconciliation Checks

Use this skill only on `task2_financial_modeler`.

## Required Checks

Before workbook build, reconcile the independent statement JSON artifacts:

- Income Statement net income must be declared as the Cash Flow Statement net income dependency.
- Cash Flow Statement ending cash must be declared as the Balance Sheet cash dependency.
- Balance Sheet retained earnings must declare net income and dividends dependencies.
- DCF input dependencies must exist for revenue, EBIT, tax, D&A, CapEx, NWC change, debt, cash, and diluted shares.
- Source gaps and `[UNSOURCED]` items must be carried into `model_audit.md`.

Critical reconciliation findings block workbook build or Task 3 handoff.

