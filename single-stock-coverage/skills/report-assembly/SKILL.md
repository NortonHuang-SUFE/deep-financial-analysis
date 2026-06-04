---
name: report-assembly
description: Assemble the final initiation report or update memo from Task 1-4 artifacts.
---

# Report Assembly

Use this skill to complete Task 5 of the single-stock coverage workflow. Task 5 assembles the final initiation report or event update memo by synthesizing artifacts from Tasks 1-4. It does not create new conclusions — it makes the analysis legible and complete.

## Core Principles

**Do not create new conclusions.** Every claim in `final_report.md` must be traceable to a specific artifact from Tasks 1-4. If a conclusion is not supported by an existing artifact, stop and flag it as a gap — do not fill the gap with unsupported analysis.

**Reference Task 1-4 files explicitly.** When making a claim, cite the source file and section (e.g., "per `business_driver_map.json` catalyst_drivers", "per `valuation_analysis.md` Sanity Check 2", "per `assumption_pack.md` Section 4.2").

**Maintain consistency across conclusions, price target, assumptions, risks, and catalysts.** The price target in the report must match `valuation_state.json`. The risks in the report must match the `risk_drivers` in `business_driver_map.json`. The key assumptions must match `assumption_pack.md`. If any inconsistency is found, resolve it before proceeding.

**Initiation reports are complete; update memos are delta-focused.** A full initiation covers all sections below. An update memo only covers sections where something has changed since the prior run.

## Pre-Assembly Checklist

Before writing, verify the following artifact chain is complete and internally consistent:

- [ ] `01_company_research/company_research.md` — covers all 7 sections (identity, business model, management, competitive, industry/policy, risks, catalysts).
- [ ] `01_company_research/business_driver_map.json` — has entries in all 6 driver categories.
- [ ] `02_financial_model/financial_facts.json` — has at least 3 years of historical data with sources.
- [ ] `02_financial_model/model_audit.md` — shows audit passed (no critical unresolved issues).
- [ ] `03_valuation/assumption_pack.md` — sections 1-9 are complete, including DCF output and reconciliation.
- [ ] `03_valuation/assumption_audit.md` — shows no FAIL items on Items 1, 8, 9; all other items documented.
- [ ] `03_valuation/valuation_analysis.md` — reconciliation table complete, 5 sanity checks documented.
- [ ] `03_valuation/valuation_state.json` — price target, rating, and sanity check verdicts populated.
- [ ] `04_charts/chart_index.json` — all required charts listed and paths verified.

If any required artifact is missing or incomplete, create a gap note and proceed with available material, flagging gaps explicitly in the report.

## Initiation Report Structure

Produce `final_report.md` with the following sections for a full initiation:

---

### Section 1: Investment Thesis

A concise statement (3-5 sentences) of the investment thesis. Synthesize from `thesis_pillars` in `coverage_state.json` and the conclusion section of `assumption_pack.md`. Include:

- The rating (Buy / Neutral / Sell) and price target (Base, with Bear and Bull range).
- The 2-3 thesis pillars that drive the view.
- The key assumption that, if wrong, would change the rating.

### Section 2: Company Overview

Synthesize from `01_company_research/company_research.md` Section 1 (Company Identity) and Section 2 (Business Model Analysis). Include:

- Company identity table: name, ticker, market, currency, fiscal year, index membership, controlling shareholder.
- Business model summary: what the company does, how it earns revenue, and what the key economic engine is.
- Revenue and segment breakdown (use charts from `04_charts/` if available).

### Section 3: Business Model and Competitive Position

Synthesize from `company_research.md` Sections 2-4. Include:

- Revenue decomposition: segments, pricing vs. volume dynamics, customer concentration.
- Competitive landscape: top competitors, moat assessment, market share trend.
- Management and governance summary: track record, incentives, governance flags.

### Section 4: Financial Model Summary

Synthesize from `02_financial_model/financial_facts.json` and `integrated_model.xlsx`. Include:

- Historical financials summary table: 5 years of revenue, EBIT margin, EBITDA margin, FCF, net debt.
- Projection summary table: Bear/Base/Bull revenue growth and EBIT margin for forecast years 1-3.
- Key model assumptions: CapEx/revenue, NWC/revenue, shares, tax rate.
- Reference `model_audit.md` status.

Do not reproduce the full three-statement model in the report — summarize and reference the workbook.

### Section 5: Valuation

Synthesize from `03_valuation/valuation_analysis.md`, `assumption_pack.md`, and `valuation_state.json`. Include:

- Valuation reconciliation table (five methods with Low/Base/High/Weight/Rationale).
- Weighted price target: Bear / Base / Bull implied prices and upside/downside from current price.
- Method narrative: brief explanation of why DCF is weighted as it is, and whether comps support or contradict the DCF.
- Sanity check summary: one line per sanity check with verdict (PASS / WARN / FAIL).
- WACC derivation and terminal growth rate with rationale.
- DCF sensitivity table: price target sensitivity to ±1% WACC and ±0.5% terminal growth.

### Section 6: Risks

Synthesize from `company_research.md` Section 6 and `risk_drivers` in `business_driver_map.json`. Include:

- Risk table with all High-severity risks.
- For each High-severity risk: mechanism (how it flows through financials), Bear-case scenario impact, and observable early warning indicator.
- Medium-severity risks summarized in a shorter table.
- Risk matrix chart from `04_charts/` if available.

### Section 7: Catalysts

Synthesize from `company_research.md` Section 7 and `catalyst_drivers` in `business_driver_map.json`. Include:

- Catalyst timeline table: near-term catalysts (0-3 months) and medium-term catalysts (3-12 months).
- For each material catalyst: direction (positive/negative/binary), magnitude, and how it affects the investment thesis or price target.
- Catalyst timeline chart from `04_charts/` if available.

---

## Update Memo Structure

For event update runs, produce a condensed `final_report.md` covering only what has changed. Reference the prior initiation report for unchanged sections.

Structure:

```markdown
## Update: [Ticker] — [Event Description] — [Date]

### Event Summary
[What happened: 1-3 sentences describing the triggering event.]

### Impact on Thesis
[Which thesis pillars are affected, and how. Reference business_driver_map.json catalyst or risk drivers.]

### Model Changes
[Which assumptions changed, by how much, and why. Reference assumption_pack.md with delta.]

### Valuation Update
[New price target (if changed) vs. prior. New Bear/Base/Bull range. Reference valuation_state.json.]

### Rating
[Maintained / Upgraded / Downgraded — with rationale.]

### Remaining Open Items
[List any [UNSOURCED] items or follow-up items that require resolution in the next update.]
```

For update memos, the delta must be explicit. State the old value and the new value for any changed assumption, target, or conclusion.

## Chart Integration

Reference charts from `04_charts/chart_index.json` throughout the report. Use the chart label and path from the index. Do not reproduce chart data in the markdown — embed or reference the chart file.

Required charts for initiation reports:
- Revenue by segment (historical and projected)
- Revenue / EBIT / FCF trend
- Margin bridge (Bear vs. Base vs. Bull)
- Scenario comparison (revenue and EBIT across scenarios)
- DCF sensitivity (price target heat map)
- Valuation football field (price target range across methods)
- Comps multiple comparison
- Historical valuation multiples
- Catalyst timeline
- Risk matrix

If a chart is not available in `chart_index.json`, note its absence in the report.

## Output

Produce the following files under `05_report/`:

### `final_report.md`

The complete initiation report or update memo per the structure above. Use the `[UNSOURCED: description]` flag inline for any claim that could not be traced to a source artifact.

### `source_index.json`

A consolidated list of all source files referenced in the report:

```json
[
  {
    "label": "string",
    "file_path": "string",
    "section_or_field": "string",
    "used_in_report_section": "string"
  }
]
```

## Quality Gate

Before marking Task 5 complete, verify:

- Price target in Section 5 matches `valuation_state.json` exactly.
- All High-severity risks in Section 6 appear in `business_driver_map.json` risk_drivers.
- All material catalysts in Section 7 appear in `business_driver_map.json` catalyst_drivers.
- No new conclusions introduced that are not traceable to a Task 1-4 artifact.
- `source_index.json` covers all Task 1-4 files cited in the report.
- `[UNSOURCED]` items are listed explicitly in `run_manifest.json` unsourced_items.
