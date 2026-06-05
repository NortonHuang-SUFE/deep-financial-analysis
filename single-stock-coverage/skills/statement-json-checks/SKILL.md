---
name: statement-json-checks
description: Validate independent Task 2 statement JSON specs before parent reconciliation.
---

# Statement JSON Checks

Use this skill on every Task 2 statement subagent.

## Required JSON Fields

Each statement JSON artifact must include:

- `statement_type`
- `canonical_row_keys`
- `line_items`
- `historical_inputs`
- `forecast_logic`
- `assumption_requirements`
- `cross_statement_dependencies`
- `source_coverage`
- `unsourced_items`
- `validation_status`

## Severity Rules

- Critical: missing canonical row keys, invalid JSON, missing source coverage, or missing cross-statement dependency declarations.
- Warning: weak assumptions, `[UNSOURCED]` facts, partial segment data, or unusual sign conventions.

Critical findings block parent reconciliation.

