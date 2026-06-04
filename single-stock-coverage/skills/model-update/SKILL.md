---
name: model-update
description: Refresh the integrated three-statement model after earnings, guidance changes, or material events without rebuilding from scratch.
---

# Model Update

Use this skill when a triggering event (earnings release, guidance revision, major announcement) requires refreshing `integrated_model.xlsx` without performing a full re-initiation. The goal is a surgical update: change only the cells that the new information affects, re-run checks, and produce an updated `financial_facts.json` and `model_audit.md`.

## When to Use

Use `model-update` instead of a full Task 2 rebuild when:

- New quarterly or annual earnings data is available for actuals replacement.
- Management has revised forward guidance (revenue, margin, capex, or NWC assumptions).
- A material event (order win, capacity change, cost announcement) changes specific line items.
- The model is being audited for formula errors without new data.

Do **not** use `model-update` for first initiation coverage — use the full Task 2 `3-statement-model` build instead.

## Required Inputs

Before starting, confirm the following files exist (from prior run via `coverage_state.json`):

- `02_financial_model/integrated_model.xlsx` — the existing workbook to update.
- `02_financial_model/financial_facts.json` — the prior structured financial data.
- `01_company_research/business_driver_map.json` — to understand what drivers changed.
- The triggering event description (from `run_manifest.json` `triggering_event` field).

## Step 1: Identify Changed Cells

Before touching the workbook, produce a change list that maps each piece of new information to the specific model cell or assumption driver it affects:

- **Actuals replacement**: new period revenue, EBIT, D&A, CapEx, NWC, net debt — replace historical hardcoded cells with new reported figures and update the `Sources` sheet citation.
- **Guidance update**: identify which assumption driver rows change (e.g., revenue growth rate in `Assumptions` tab, CapEx/revenue in `Assumptions` tab).
- **Event impact**: identify which revenue or cost line is affected and whether the change propagates through formula linkages automatically or requires an assumption override.

Document the change list in a delta block:

```
## Model Update Delta
Triggering event: [description]
Changes:
  - [Sheet]![Cell]: old value → new value | reason
  - ...
```

Write this delta block as the first section of the updated `model_audit.md`.

## Step 2: Apply Changes to Workbook

Using `build_excel_model` or direct workbook manipulation via iFind MCP:

1. Update the `Sources` sheet with new data references for any new actuals.
2. Replace hardcoded historical figures with the new reported values.
3. Update assumption driver cells in the `Assumptions` tab for any guidance changes.
4. Do **not** change formula cells — verify that formula linkages update automatically when assumption inputs change.
5. If new assumption drivers require a new row (e.g., a new segment was disclosed), add the row with a sourced value and link it through the model.

**Mandatory constraint**: All forecasts, subtotals, and checks must remain formula-driven. Only hardcoded cells in `Assumptions`, `Sources`, and historical data columns may be changed.

## Step 3: Re-run Model Integrity Checks

After applying changes, verify that all Checks sheet items still pass:

- Balance sheet balance (Assets = Liabilities + Equity) for all forecast years.
- Cash tie-out (Opening + CF = Closing) for all forecast years.
- NI link (IS Net Income = BS Retained Earnings delta + Dividends).
- RE roll-forward.
- CapEx / PP&E tie.
- Debt tie (Opening + Drawdowns - Repayments = Closing).

If any check breaks, fix the root cause before proceeding. Do not proceed to Task 3 with a broken model.

## Step 4: Run audit_excel_model

Call `audit_excel_model` on the updated `integrated_model.xlsx`. Write the full audit result to `model_audit.md` under `02_financial_model/`. The audit result must show `"passed": true` before the model update is considered complete.

If `"passed": false`, fix the reported issues and re-run the audit. Record any issues found and resolved in `model_audit.md` under an "Audit History" section.

## Step 5: Update financial_facts.json

Refresh `financial_facts.json` to reflect:

- New actuals for the most recent period (replace projected values with reported figures).
- Updated model projection summary reflecting the new assumption inputs.
- Updated `[UNSOURCED]` list if any prior gaps were resolved by the new data.
- Updated source strings for new actuals.

The updated `financial_facts.json` must cover the same fields as the initiation version:

- historical and projected revenue, EBIT, EBITDA, net income
- D&A, CapEx, NWC change
- debt, cash, shares
- segment revenue and margin if available
- model projection summary (Bear/Base/Bull for key metrics)
- source strings and `[UNSOURCED]` list

## Step 6: Document Delta for Task 3

After `model_audit.md` and `financial_facts.json` are updated, produce a delta summary that Task 3 will consume to determine which valuation assumptions need revision:

```json
{
  "model_update_delta": {
    "triggering_event": "string",
    "actuals_updated": ["string"],
    "assumptions_changed": [
      {
        "driver": "string",
        "old_value": "string or number",
        "new_value": "string or number",
        "reason": "string"
      }
    ],
    "checks_status": "all_pass | issues_found_and_resolved | issues_remain",
    "audit_passed": true,
    "valuation_rerun_required": true,
    "valuation_drivers_affected": ["string"]
  }
}
```

Write this as `model_update_delta.json` under `02_financial_model/`. Task 3 reads this file to scope which assumptions require revision.

## Output

Produce the following files under `02_financial_model/`:

- `integrated_model.xlsx` — updated workbook (overwrite in the new run directory, not the prior run).
- `financial_facts.json` — refreshed structured data.
- `model_audit.md` — audit result with delta block and audit history.
- `model_update_delta.json` — delta summary for Task 3.

## Xlsx-Author Integration

When building or modifying Excel workbooks, use the `build_excel_model` tool (the xlsx-author capability) to create stub workbooks and the `audit_excel_model` tool to validate them. For headless workbook generation:

- Use `build_excel_model` to scaffold a new workbook with standard sheets when a full rebuild is needed.
- For surgical cell-level changes, use iFind MCP tools or direct openpyxl manipulation to update specific cells without rebuilding the full workbook structure.
- Always call `audit_excel_model` after any workbook modification.

## Quality Gate

Before passing control to Task 3:

- `model_audit.md` must record `audit_excel_model` result with `"passed": true`.
- `financial_facts.json` must be updated with the most recent actuals.
- `model_update_delta.json` must identify at least one affected assumption or confirm no valuation assumptions changed (in which case Task 3 valuation rerun may be skipped).
- All Checks sheet formulas must resolve without errors.
