---
name: income-statement-model
description: Create sourced Revenue Build and Income Statement JSON specs for Task 2 without writing Excel.
---

# Income Statement Model

Use this skill only for `is_modeler`.

## Scope

Produce independent JSON specs for:

- `02_financial_model/revenue_build_spec.json`
- `02_financial_model/income_statement_spec.json`

Do not create, open, edit, or save `integrated_model.xlsx`. Do not read sibling statement JSON. The parent owns reconciliation and handoff gates; workbook_builder owns workbook build, workbook validation, and audit handoff.

## Required JSON Content

The JSON must include the shared `statement-json-checks` required fields plus:

- Revenue build detail by segment, product, geography, or driver when supported by Task 1 evidence.
- Historical revenue, gross profit, EBIT, EBITDA, interest expense, pretax income, tax expense, net income, D&A, diluted shares, and EPS where available.
- Forecast logic that references assumptions and dependency keys rather than hardcoded projections.
- Source coverage for every historical fact and every externally sourced assumption.

## Canonical Keys

Include these canonical row keys exactly:

- `revenue_total`
- `gross_profit`
- `ebit`
- `ebitda`
- `interest_expense`
- `pretax_income`
- `tax_expense`
- `net_income`
- `da_total`

## Dependency Declarations

Declare dependencies for:

- `revenue_build.total_revenue`
- `debt_interest.interest_expense`
- `share_count.diluted_shares`

## Checks

- Critical: missing canonical key, missing source coverage, invalid sign convention, or missing dependency declaration.
- Warning: `[UNSOURCED]` facts, partial segment data, weak revenue driver evidence, or forecast logic that cannot be cleanly assumption-linked.

Critical findings must be resolved before calling `write_income_statement_json`.

