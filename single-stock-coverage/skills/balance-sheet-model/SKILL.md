---
name: balance-sheet-model
description: Create sourced Balance Sheet JSON specs for Task 2 without writing Excel.
---

# Balance Sheet Model

Use this skill only for `bs_modeler`.

## Scope

Produce `02_financial_model/balance_sheet_spec.json`.

Do not create, open, edit, or save `integrated_model.xlsx`. Do not read sibling statement JSON. The parent owns reconciliation and handoff gates; workbook_builder owns workbook build, workbook validation, and audit handoff.

## Required JSON Content

The JSON must include the shared `statement-json-checks` required fields plus:

- Assets: cash, working-capital accounts, PP&E, other assets, total assets.
- Liabilities: current liabilities, debt, other liabilities, total liabilities.
- Equity: common stock/APIC, retained earnings, total equity, total liabilities and equity.
- Retained earnings roll-forward logic.
- Source coverage for every historical balance sheet fact and every externally sourced assumption.

## Canonical Keys

Include these canonical row keys exactly:

- `cash_and_equivalents`
- `total_current_assets`
- `total_assets`
- `total_current_liabilities`
- `total_debt`
- `retained_earnings`
- `total_equity`
- `total_liabilities_and_equity`

## Dependency Declarations

Declare dependencies for:

- `cash_flow.ending_cash`
- `income_statement.net_income`
- `share_count.dividends`

## Checks

- Critical: missing canonical key, missing source coverage, missing cash dependency, missing retained earnings dependency, or no total liabilities plus equity tie.
- Warning: `[UNSOURCED]` facts, unclear retained earnings bridge, unusual sign convention, or unsupported balance sheet assumption.

Critical findings must be resolved before calling `write_balance_sheet_json`.

