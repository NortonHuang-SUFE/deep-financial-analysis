---
name: coverage-state
description: Read and write the persistent coverage state for a ticker across runs.
---

# Coverage State

Use this skill to read and update the persistent coverage state for a ticker. The coverage state is the single source of truth that links all runs together, enables incremental updates, and prevents the agent from losing context between sessions.

## File and Directory Structure

All coverage artifacts are stored under a root coverage directory:

```
coverage/{market}-{ticker}/
  coverage_state.json
  runs/{YYYYMMDD-HHMMSS}/
    run_manifest.json
    01_company_research/
    02_financial_model/
    03_valuation/
    04_charts/
    05_report/
```

- `{market}` is the exchange or market identifier (e.g., `sha`, `szse`, `hkex`, `nyse`).
- `{ticker}` is the ticker symbol in lowercase (e.g., `600519`, `00700`, `nvda`).
- Each run gets a timestamped subdirectory in ISO-like format: `YYYYMMDD-HHMMSS`.

## `coverage_state.json` Schema

`coverage_state.json` lives at the root of the ticker directory and is updated after every run. It records the latest known state of coverage for the ticker.

```json
{
  "ticker": "string",
  "market": "string",
  "company": "string",
  "currency": "string",
  "fiscal_year_end": "string",
  "coverage_status": "initiated | active | stale | suspended",
  "latest_run_id": "string",
  "latest_run_path": "string",
  "latest_task_type": "initiation | update | valuation_refresh | model_audit",
  "latest_company_research_path": "string or null",
  "latest_model_path": "string or null",
  "latest_valuation_state_path": "string or null",
  "latest_report_path": "string or null",
  "price_target": {
    "bear": "number or null",
    "base": "number or null",
    "bull": "number or null",
    "currency": "string",
    "as_of_date": "YYYY-MM-DD"
  },
  "rating": "Buy | Neutral | Sell | Not Rated",
  "current_price": "number or null",
  "current_price_date": "YYYY-MM-DD or null",
  "thesis_pillars": ["string"],
  "key_assumptions": {
    "base_revenue_growth_pct": "number or null",
    "base_ebit_margin_pct": "number or null",
    "wacc_pct": "number or null",
    "terminal_growth_pct": "number or null"
  },
  "next_catalysts": [
    {
      "catalyst": "string",
      "timing": "string",
      "direction": "positive | negative | binary",
      "magnitude": "material | moderate | minor"
    }
  ],
  "stale_data_flags": ["string"],
  "unsourced_items": ["string"],
  "last_updated": "ISO 8601 datetime"
}
```

**Field notes:**
- `coverage_status`: set to `stale` if the latest model is older than 90 days or if a material event has occurred since the last run without a corresponding update.
- `stale_data_flags`: list specific data items that are known to be outdated (e.g., "Q3 earnings not yet reflected in model", "peer set not refreshed since initiation").
- `thesis_pillars`: 2-4 concise strings that summarize the core investment thesis (e.g., "Market share gain in EV battery segment", "Margin recovery from cost normalization").

## `run_manifest.json` Schema

`run_manifest.json` lives inside each run subdirectory and records everything about that specific run.

```json
{
  "run_id": "string",
  "ticker": "string",
  "market": "string",
  "company": "string",
  "run_timestamp": "ISO 8601 datetime",
  "task_type": "initiation | update | valuation_refresh | model_audit",
  "triggering_event": "string",
  "tasks_executed": ["task1_company_research", "task2_financial_model", "task3_valuation", "task4_charts", "task5_report"],
  "input_artifacts": [
    {
      "label": "string",
      "path": "string"
    }
  ],
  "output_artifacts": [
    {
      "label": "string",
      "path": "string"
    }
  ],
  "final_conclusion": {
    "price_target_base": "number or null",
    "rating": "string",
    "thesis_summary": "string"
  },
  "unsourced_items": ["string"],
  "follow_up_checklist": ["string"],
  "errors_or_warnings": ["string"]
}
```

**Field notes:**
- `triggering_event`: a short description of what initiated this run (e.g., "First initiation coverage", "Q3 2025 earnings release", "Management guidance cut", "Policy announcement").
- `tasks_executed`: list only the tasks that were actually run in this execution (not tasks skipped).
- `input_artifacts`: paths to files read as inputs (e.g., the previous run's `valuation_state.json` or `financial_facts.json`).
- `output_artifacts`: paths to all files produced in this run.
- `follow_up_checklist`: specific items to verify or resolve in the next update (e.g., "Confirm Q4 capacity utilization in next earnings call", "Re-run comps after peer X reports").

## When to Read Coverage State

Read `coverage_state.json` at the start of every run, before executing any task:

1. **Determine run type**: if `coverage_status` is null or no file exists, this is an initiation run. If the file exists, this is an update.
2. **Load prior artifacts**: use `latest_model_path`, `latest_company_research_path`, and `latest_valuation_state_path` to locate prior outputs that can be reused or updated incrementally.
3. **Check staleness**: review `stale_data_flags` to understand what data must be refreshed.
4. **Load thesis context**: load `thesis_pillars` and `key_assumptions` to provide Task 3 with the prior valuation baseline.
5. **Carry forward unsourced items**: review `unsourced_items` to determine if prior data gaps have been resolved.

## When to Update Coverage State

Update `coverage_state.json` after every run completes, once all artifacts are on disk.

Write the following fields at minimum:
- `latest_run_id`, `latest_run_path`, `latest_task_type`
- All `latest_*_path` fields for tasks that were executed.
- `price_target`, `rating`, `current_price`, `current_price_date` — if Task 3 or Task 5 was executed.
- `thesis_pillars`, `key_assumptions` — if Task 1 or Task 3 was executed.
- `next_catalysts` — if Task 1 was executed.
- `stale_data_flags` — update to reflect what is now stale based on the current run's conclusions.
- `unsourced_items` — update with any unresolved `[UNSOURCED]` items from the current run.
- `last_updated` — always update this field.

Set `coverage_status`:
- `initiated` — after the first successful completion of all 5 tasks.
- `active` — after any successful update run.
- `stale` — if errors occurred, critical data is missing, or the run was partial.

## Routing Update Events to Tasks

When the triggering event is not a full initiation, use the following routing table to determine which tasks need to run:

| Event type | Tasks to run |
|---|---|
| Earnings / results release | Task 2 (model-update) → Task 3 (valuation) → Task 5 (update memo) |
| Guidance change | Task 2 (assumptions update) → Task 3 |
| Large share price move | Task 3 (valuation refresh only) |
| Major order / capacity / price announcement | Task 1 (delta) → Task 2 (if numbers change) → Task 3 |
| Policy / regulatory / penalty | Task 1 (delta) → Task 3 (assumption audit) → thesis impact |
| Model audit request | Task 2 (audit-xls) → fix checklist |
| Pre-earnings | Task 3 (scenario refresh) → watch item list |

When routing a partial run, load the unchanged artifacts from the prior run via `coverage_state.json` rather than re-running the full pipeline. Record all input artifact paths in `run_manifest.json` so the provenance chain is preserved.

## Delta Output Requirement

Every update run must document a delta section in its `run_manifest.json` `follow_up_checklist` field, and in the update memo produced by Task 5:

- What new event occurred.
- Which value driver or thesis pillar is affected.
- Which model assumptions changed and by how much.
- Whether the price target or rating changed.
- Which items remain `[UNSOURCED]` and have not been resolved.
