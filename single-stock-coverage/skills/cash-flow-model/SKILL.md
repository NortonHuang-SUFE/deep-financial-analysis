---
name: cash-flow-model
description: Create sourced Cash Flow Statement JSON specs for Task 2 without writing Excel.
---

# Cash Flow Model

Use this skill only for `cf_modeler`.

## Scope

Produce `02_financial_model/cash_flow_statement_spec.json`.

Do not write or edit `integrated_model.xlsx`. Do not read sibling statement JSON.

## Required Checks

- Every historical cash flow fact must include a source string or `[UNSOURCED]`.
- Net income, D&A addback, NWC change, CFO, CapEx, CFI, financing flows, beginning cash, and ending cash must use canonical row keys.
- Declare cross-statement dependencies for net income, D&A, NWC change, CapEx, debt movements, dividends, and ending cash.
- State cash flow sign conventions explicitly.

