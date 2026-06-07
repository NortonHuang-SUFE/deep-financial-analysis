---
name: statement-json-checks
description: Validate independent Task 2 statement JSON specs before parent reconciliation.
---

# Statement JSON Checks

Use this skill on every Task 2 statement subagent.

## Required Fields

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

## Validation Procedure

1. Confirm `statement_type` matches the subagent.
2. Confirm every required field is present and non-empty when applicable.
3. Confirm each `historical_inputs` record has `period`, `canonical_key`, `value`, `source`, and unit/currency where relevant.
4. Confirm canonical row keys use the exact names required by that statement skill.
5. Confirm `cross_statement_dependencies` declares all parent reconciliation links.
6. Confirm `source_coverage` covers each historical input and sourced assumption.
7. Confirm every missing or inferred fact appears in `unsourced_items`.
8. Confirm `forecast_logic` is formula-oriented and assumption-linked, not a hardcoded forecast table.
9. Call the statement-specific validate tool.
10. Fix Critical findings before writing the JSON artifact.

## Severity

- Critical: invalid JSON, wrong statement type, missing required field, missing canonical key, missing source coverage, or missing cross-statement dependency.
- Warning: `[UNSOURCED]` facts, weak assumptions, partial source coverage, unusual sign conventions, or hardcode risk.

Critical findings block parent reconciliation. Warnings must flow into `model_audit.md`.
