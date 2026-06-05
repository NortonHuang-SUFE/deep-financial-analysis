---
name: balance-sheet-model
description: Create sourced Balance Sheet JSON specs for Task 2 without writing Excel.
---

# Balance Sheet Model

Use this skill only for `bs_modeler`.

## Scope

Produce `02_financial_model/balance_sheet_spec.json`.

Do not write or edit `integrated_model.xlsx`. Do not read sibling statement JSON.

## Required Checks

- Every historical balance sheet fact must include a source string or `[UNSOURCED]`.
- Cash, working-capital accounts, PP&E, debt, retained earnings, equity, total assets, and total liabilities plus equity must use canonical row keys.
- Declare cross-statement dependencies for cash, retained earnings, debt, PP&E, and working capital.
- Include retained earnings roll-forward logic and any source gaps that could affect the roll-forward.

