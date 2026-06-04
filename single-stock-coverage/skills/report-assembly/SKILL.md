---
name: report-assembly
description: Assemble single-stock coverage initiation reports and update memos from completed Task 1-4 artifacts without changing upstream conclusions.
---

# Report Assembly

Use this skill for Task 5 of the `single-stock-coverage` workflow. It assembles
the final written deliverable from completed Task 1-4 artifacts.

Task 5 is not a research, modeling, valuation, or chart-generation task. It is
a controlled assembly step that preserves upstream conclusions and makes their
source trail explicit.

## Core Rule

Depend on Task 1-4 artifacts. Do not recreate or revise them.

- Do not perform new company, industry, market, or news research.
- Do not modify model assumptions or financial projections.
- Do not modify valuation method weights, WACC, terminal growth, scenario
  values, rating, target price, or recommendation.
- Do not invent missing source citations, charts, tables, or conclusions.
- If upstream artifacts disagree, stop and return the issue to the task that
  owns the disputed fact.

Ownership of corrections:

| Issue | Return to |
| --- | --- |
| Company identity, business model, management, industry, competition, risk, catalyst, thesis fact | Task 1 |
| Historical data, projection data, workbook links, model checks, financial source gaps | Task 2 |
| Assumptions, scenario outputs, valuation method weights, rating, target price, valuation range | Task 3 |
| Missing, stale, unreadable, or inconsistent charts and chart metadata | Task 4 |
| Missing prior state or event context for an update memo | Parent router / coverage-state manager |

## Inputs

Expected run layout:

```text
coverage/{market}-{ticker}/
  coverage_state.json
  runs/{YYYYMMDD-HHMMSS}/
    run_manifest.json
    01_company_research/
      company_research.md
      business_driver_map.json
      source_log.json
    02_financial_model/
      integrated_model.xlsx
      financial_facts.json
      model_audit.md
    03_valuation/
      evidence_sufficiency.md
      value_driver_map.json
      assumption_pack.md
      assumption_audit.md
      dcf_model.xlsx
      comps.xlsx
      precedent_transactions.xlsx
      valuation_analysis.md
      valuation_state.json
    04_charts/
      chart_pack/
      chart_index.json
```

Required artifacts for an initiation report:

- Task 1 company research, business driver map, and source log.
- Task 2 integrated model, financial facts, and model audit.
- Task 3 evidence sufficiency, assumption pack, assumption audit, valuation
  analysis, valuation state, and valuation workbooks where applicable.
- Task 4 chart index and referenced chart files.

Required artifacts for an update memo:

- Current run artifacts for every rerun task.
- Prior `coverage_state.json` or prior run context.
- Triggering event metadata from `run_manifest.json` or parent instructions.
- Existing unaffected upstream artifacts, if the memo needs to restate baseline
  thesis, prior target price, prior assumptions, or prior catalysts.

## Outputs

Write outputs to `05_report/` in the current run directory:

```text
05_report/
  final_report.md
  final_report.docx  # optional
  source_index.json
```

`final_report.md` is always required. `source_index.json` is always required.
`final_report.docx` is optional and should be created only when requested,
when the run contract requires it, or when document tooling is already part of
the execution environment.

Do not create extra completion summaries or separate ad hoc source files.

## Report Kind Selection

Set `report_kind` to one of:

- `initiation`: first coverage or full refreshed coverage.
- `update_memo`: event-driven delta after prior coverage exists.

Use the parent request first, then `run_manifest.task_type`, then available
state. If the report kind cannot be determined, ask the parent agent to clarify
before writing the report.

## Initiation Report Structure

An initiation report may be comprehensive. Use this structure unless the parent
requests a house style:

1. Title page / investment summary
   - Company, ticker, market, currency, fiscal year, report date.
   - Rating, target price, valuation range, current price, upside/downside,
     market cap, enterprise value, and time horizon from Task 3/state.
   - Three to five thesis bullets sourced from Task 1 and Task 3.
   - Summary financial table from Task 2.
   - First chart from Task 4, usually stock price performance or valuation
     summary if available.
2. Investment thesis
   - Thesis pillars from Task 1 and Task 3.
   - Quantitative support from Task 2.
   - Charts from Task 4.
3. Company overview
   - Business model, segments, geography, customers, management, governance,
     industry context, and competition from Task 1.
4. Business drivers and catalysts
   - Driver map from Task 1 and value driver map from Task 3.
   - Upcoming catalysts and falsifiable indicators from Task 1/3.
5. Financial analysis
   - Historical and projected financials from Task 2.
   - Revenue build, margin drivers, cash flow, balance sheet, working capital,
     capex, and model audit limitations.
6. Assumptions and scenarios
   - Bear/Base/Bull assumptions and logic from Task 3.
   - Scenario comparison, sensitivity, and audit findings from Task 3.
7. Valuation
   - DCF, trading comps, precedent transactions if applicable, historical
     multiples, market-implied checks, valuation reconciliation, method weights,
     rating, target price, and risks to target from Task 3.
8. Risks
   - Business, financial, governance, regulatory, market, and valuation risks
     from Task 1 and Task 3.
9. Appendices
   - Supplemental tables and chart references.
   - `[UNSOURCED]` list.
   - Human-readable artifact index.
   - Source methodology note.

## Update Memo Structure

An update memo is a delta document. Keep it focused on what changed.

1. Header
   - Company, ticker, market, report date, event date, event type, prior rating
     and target price, updated rating and target price.
2. Bottom line
   - One paragraph stating the conclusion exactly as supported by Task 3 or the
     rerun upstream task.
3. Event summary
   - What happened, when it happened, and which upstream artifact supports it.
4. Delta table
   - Prior view, new evidence, affected driver, affected task, model/valuation
     impact, and report conclusion.
5. Thesis impact
   - Which thesis pillars are strengthened, weakened, unchanged, or untested.
6. Model and assumption impact
   - Only changes already made by Task 2/3 reruns.
   - State "unchanged" when upstream artifacts explicitly show no change.
7. Valuation and recommendation
   - Rating, target price, valuation range, and scenario impact copied from
     Task 3.
8. Catalysts, risks, and watch items
   - Updated or unchanged items from Task 1/3 and `coverage_state.json`.
9. Source and artifact appendix
   - `[UNSOURCED]` list.
   - Human-readable artifact index.

Do not include a full Company 101 section in an update memo unless the event
changes company fundamentals or the parent requests a full refreshed report.

## Source Index

Create `source_index.json` as the machine-readable source trail for the final
report. It must include both source entries and an artifact index.

Recommended schema:

```json
{
  "schema_version": "1.0",
  "report_kind": "initiation",
  "company": "",
  "ticker": "",
  "market": "",
  "run_id": "",
  "report_path": "05_report/final_report.md",
  "docx_path": null,
  "generated_at": "",
  "upstream_conclusion_lock": {
    "rating": "",
    "target_price": null,
    "valuation_range": {"low": null, "base": null, "high": null},
    "source_artifact": "03_valuation/valuation_state.json"
  },
  "artifacts": [
    {
      "artifact_id": "task1_company_research",
      "task": 1,
      "path": "01_company_research/company_research.md",
      "required": true,
      "role": "company facts, thesis pillars, risks, catalysts",
      "status": "used"
    }
  ],
  "sources": [
    {
      "source_id": "S001",
      "task": 1,
      "artifact_id": "task1_company_research",
      "artifact_path": "01_company_research/company_research.md",
      "source_type": "upstream_artifact",
      "source_label": "Task 1 company_research.md",
      "url": null,
      "as_of_date": null,
      "used_in_sections": ["Company overview", "Risks"],
      "claims": ["Business model description", "Risk factor list"]
    }
  ],
  "charts": [
    {
      "figure_id": "F001",
      "chart_id": "",
      "title": "",
      "path": "04_charts/chart_pack/example.png",
      "source_chart_index": "04_charts/chart_index.json",
      "used_in_section": "Investment summary",
      "upstream_tasks": [1, 2, 3, 4]
    }
  ],
  "tables": [
    {
      "table_id": "T001",
      "title": "Summary financials",
      "source_artifact": "02_financial_model/financial_facts.json",
      "used_in_section": "Investment summary"
    }
  ],
  "unsourced_items": [],
  "consistency_checks": [
    {
      "check": "Target price matches valuation_state.json",
      "status": "pass",
      "details": ""
    }
  ],
  "blocked_items": []
}
```

Rules:

- Every report section must map to one or more source entries.
- Every chart in the report must appear in `charts`.
- Every table in the report must appear in `tables`.
- `artifacts` is the artifact index. Do not create a separate artifact index
  file unless the parent explicitly requests it.
- If an upstream source log contains original URLs or filing references, carry
  those references into `sources` without inventing missing metadata.
- Keep `[UNSOURCED]` items visible in `unsourced_items`.

## Human-Readable Artifact Index

Append a short artifact index to `final_report.md`:

```markdown
## Artifact Index

| Artifact | Task | Path | Used for |
| --- | --- | --- | --- |
| Company research | Task 1 | `01_company_research/company_research.md` | Business facts, risks, catalysts |
| Financial facts | Task 2 | `02_financial_model/financial_facts.json` | Summary financials, projections |
| Valuation state | Task 3 | `03_valuation/valuation_state.json` | Rating, target price, valuation range |
| Chart index | Task 4 | `04_charts/chart_index.json` | Figure list and chart paths |
```

This table is for readers. The canonical machine-readable artifact index lives
inside `source_index.json.artifacts`.

## Consistency Gates

Run these checks before writing final outputs:

- Required artifacts exist and are readable.
- Company name, ticker, market, currency, and fiscal year are consistent across
  tasks.
- Rating, recommendation, target price, valuation range, WACC, terminal growth,
  and scenario outputs match Task 3.
- Historical and projected financial summaries match Task 2.
- Thesis pillars, risks, catalysts, and company facts match Task 1.
- Charts are listed in Task 4 `chart_index.json` and their captions do not
  contradict Task 1-3.
- Update memo deltas are backed by rerun task artifacts and prior coverage
  state.
- All `[UNSOURCED]` items from Task 1-4 are carried into the report appendix or
  `source_index.json`.

If a check fails, do not write a polished report that hides the issue. Return a
blocked note to the parent with:

- The failed check.
- The conflicting or missing artifact paths.
- The conflicting values if applicable.
- The upstream task that must resolve the issue.

## Quality Checklist

Before finalizing:

- [ ] `final_report.md` exists under `05_report/`.
- [ ] `source_index.json` exists under `05_report/`.
- [ ] `final_report.docx` exists if requested or required.
- [ ] Report kind is clearly marked as `initiation` or `update_memo`.
- [ ] Every section uses Task 1-4 artifacts as support.
- [ ] No new research, unsupported assumptions, or changed target price appear
      in the report.
- [ ] Rating, target price, recommendation, valuation range, and method weights
      match Task 3.
- [ ] Financial tables and metrics match Task 2.
- [ ] Company facts, risks, catalysts, and thesis pillars match Task 1.
- [ ] Figures reference valid Task 4 chart files.
- [ ] `source_index.json.artifacts` contains all required input artifacts.
- [ ] `source_index.json.sources` maps report sections to upstream artifacts.
- [ ] `source_index.json.charts` maps every figure to `chart_index.json`.
- [ ] `source_index.json.tables` maps every table to its source artifact.
- [ ] `[UNSOURCED]` items are visible and not silently removed.
- [ ] Update memo includes prior vs. current deltas, affected drivers, affected
      tasks, and unchanged items where relevant.
- [ ] Final response lists output paths and any unresolved upstream limitations.

## Final Response

Return a concise completion note with:

- Report kind.
- Paths to `final_report.md` and `source_index.json`.
- Path to `final_report.docx` if created.
- Confirmation that Task 5 did not change assumptions, rating, or target price.
- Any blocked upstream issues if assembly could not be completed.
