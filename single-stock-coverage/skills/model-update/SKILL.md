---
name: model-update
description: Refresh an existing Task 2 financial model for new earnings, guidance, macro changes, or company-specific events while rerunning only affected model sections.
---

# Model Update

Use this skill when a Task 2 model already exists and new information requires a refresh. Preserve the existing model architecture and update only the affected inputs, formulas, schedules, checks, and downstream outputs.

## Update Triggers

Cover all of these trigger types:

- Earnings updates: quarterly, semiannual, annual, preliminary results, restatements, or segment disclosures.
- Guidance updates: management revenue, margin, CapEx, production, volume, pricing, tax, cash flow, buyback, debt, or long-term target guidance.
- Macro updates: interest rates, FX, commodity prices, inflation, wage costs, tax rules, policy rates, market risk assumptions, or demand indicators.
- Event updates: M&A, divestitures, restructuring, plant openings/closures, product launches, regulatory changes, management changes, litigation, financing, buybacks, dividends, or capital raises.

## Principle: Rerun Only Affected Parts

Do not rebuild the entire model by default. Identify the dependency path and rerun only the affected portions:

- New reported actuals affect historical periods, roll-forwards, run-rate assumptions, and checks for the updated period.
- Revenue guidance affects `Assumptions`, `Revenue Build`, `Income Statement`, `Working Capital`, and `DCF Inputs`.
- Margin guidance affects `Assumptions`, `Income Statement`, taxes, cash flow, and `DCF Inputs`.
- CapEx or capacity updates affect `Assumptions`, `PP&E / D&A`, `Cash Flow Statement`, `Balance Sheet`, and `DCF Inputs`.
- Debt, interest, rates, or refinancing updates affect `Debt / Interest`, `Income Statement`, `Cash Flow Statement`, `Balance Sheet`, and checks.
- Share repurchases, issuance, options, or convertibles affect `Share Count`, EPS, cash flow, equity, and per-share DCF inputs.
- Macro updates should flow through the assumptions they actually change; do not alter company operating drivers without evidence.
- Events should update the specific schedule and statements they touch, then refresh dependent checks and DCF inputs.

## Workflow

1. Snapshot the prior model state: model date, source set, key assumptions, key outputs, and audit status.
2. Classify the update trigger as earnings, guidance, macro, event, or a combination.
3. Add new sources to `Sources` and update `financial_facts.json`.
4. Plug new actuals or assumptions only in hardcoded input cells with source references.
5. Recalculate only affected schedules and statements by preserving existing formulas and links.
6. Refresh all directly affected downstream outputs, especially `DCF Inputs`.
7. Run the required checks for affected periods and any downstream periods.
8. Run `audit-xls` on the updated workbook before delivery.
9. Update `model_audit.md` with what changed, what reran, what did not rerun, and remaining issues.

## Update Summary

Document:

- Prior estimate vs actual or prior assumption vs new assumption.
- Source and date of the new information.
- Affected workbook tabs and line items.
- Estimate deltas for revenue, EBITDA/EBIT, net income, EPS, FCF, debt, cash, and shares where relevant.
- Whether the update changes Task 3 DCF inputs materially.
- Any `[UNSOURCED]` or judgment-based adjustments.

## Audit Gate

After any update:

- BS balance must still pass.
- Cash tie-out must still pass.
- NI link, RE roll-forward, CapEx/PP&E tie, and debt tie must still pass.
- Any failed Critical check blocks clean handoff to Task 3 unless explicitly documented as unresolved.
