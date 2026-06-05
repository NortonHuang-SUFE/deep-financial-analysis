---
name: income-statement-model
description: Create sourced Revenue Build and Income Statement JSON specs for Task 2 without writing Excel.
---

# Income Statement Model

Use this skill only for `is_modeler`.

## Scope

Produce JSON specs for:

- `02_financial_model/revenue_build_spec.json`
- `02_financial_model/income_statement_spec.json`

Do not write or edit `integrated_model.xlsx`. Do not read sibling statement JSON.

## Required Checks

- Every historical fact must include a source string or `[UNSOURCED]`.
- Forecast logic must reference assumption drivers, not hardcoded projections.
- Revenue, gross profit, EBIT, EBITDA, pre-tax income, tax, net income, D&A, diluted shares, and EPS must use canonical row keys.
- Declare cross-statement dependencies for net income, D&A, interest expense, diluted shares, and revenue build total.

