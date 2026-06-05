---
name: cash-flow-model
description: Create sourced Cash Flow Statement JSON specs for Task 2 without writing Excel.
---

# Cash Flow Model

Use this skill only for `cf_modeler`.

## Scope

Produce `02_financial_model/cash_flow_statement_spec.json`.

Do not create, open, edit, or save `integrated_model.xlsx`. Do not read sibling statement JSON. The parent owns reconciliation, workbook build, workbook validation, and audit handoff.

## Required JSON Content

The JSON must include the shared `statement-json-checks` required fields plus:

- Indirect CFO: net income, D&A addback, NWC change, other operating adjustments, CFO total.
- CFI: CapEx, acquisitions/divestitures where material, CFI total.
- CFF: debt movements, dividends, buybacks/issuance where material, CFF total.
- Cash bridge: beginning cash, net change in cash, ending cash.
- Source coverage for every historical cash flow fact and every externally sourced assumption.

## Canonical Keys

Include these canonical row keys exactly:

- `net_income_cf`
- `da_addback`
- `nwc_change`
- `cfo_total`
- `capex`
- `cfi_total`
- `debt_proceeds_repayments`
- `dividends`
- `cff_total`
- `beginning_cash`
- `ending_cash`

## Dependency Declarations

Declare dependencies for:

- `income_statement.net_income`
- `ppe_da.da_total`
- `balance_sheet.cash_and_equivalents`

## Checks

- Critical: missing canonical key, missing source coverage, missing cash bridge dependency, unclear sign convention, or missing net income dependency.
- Warning: `[UNSOURCED]` facts, unsupported cash bridge assumption, unclear NWC convention, or forecast logic that cannot be formula-linked.

Critical findings must be resolved before calling `write_cash_flow_json`.

