---
name: chart-pack
description: Generate the Task 4 chart pack for single-stock coverage using only completed Task 1-3 artifacts, with a chart_pack directory and traceable chart_index.json for Task 5 report assembly.
---

# Chart Pack

Generate Task 4 charts for the single-stock-coverage workflow. This skill turns
completed Task 1-3 artifacts into report-ready financial charts and an index that
Task 5 can use for report assembly.

## Hard Boundaries

- Use only facts, model outputs, and valuation outputs already written by Task 1,
  Task 2, and Task 3.
- Do not conduct new research.
- Do not fetch stock prices, peer data, filings, news, estimates, or market data.
- Do not alter Task 3 valuation conclusions, including target price, rating,
  recommendation, scenario values, DCF assumptions, comps outputs, valuation
  ranges, or method weights.
- Do not create placeholder charts or synthetic chart data.
- If required upstream artifacts or fields are missing, stop and request that the
  relevant upstream task be completed or repaired.

## Required Inputs

Start from the active run directory:

```text
out/coverage/{market}-{ticker}/runs/{YYYYMMDD-HHMMSS}/
```

Required artifacts:

```text
01_company_research/company_research.md
01_company_research/business_driver_map.json
01_company_research/source_log.json
02_financial_model/integrated_model.xlsx
02_financial_model/financial_facts.json
02_financial_model/model_audit.md
03_valuation/evidence_sufficiency.md
03_valuation/value_driver_map.json
03_valuation/assumption_pack.md
03_valuation/assumption_audit.md
03_valuation/dcf_model.xlsx
03_valuation/comps.xlsx
03_valuation/valuation_analysis.md
03_valuation/valuation_state.json
```

Optional Task 3 artifact:

```text
03_valuation/precedent_transactions.xlsx
```

## Mandatory Chart Inventory

The chart pack must include these charts. Use the listed source ownership and
fields as the default contract; adapt field names only to match the actual Task
1-3 schema while preserving the same information content.

| Chart id | Required chart | Primary source artifact | Required data fields | Chart purpose |
| --- | --- | --- | --- | --- |
| `revenue_by_segment` | Revenue by segment | `02_financial_model/financial_facts.json`; `02_financial_model/integrated_model.xlsx` | fiscal years; historical and forecast segment revenue; segment labels; total revenue | Show revenue mix, segment contribution, and forecast mix shift. |
| `revenue_ebit_fcf_trend` | Revenue / EBIT / FCF trend | `02_financial_model/financial_facts.json`; `02_financial_model/integrated_model.xlsx` | fiscal years; revenue; EBIT; free cash flow; historical/forecast flag | Show operating scale, profit conversion, and cash generation trajectory. |
| `margin_bridge` | Margin bridge | `02_financial_model/financial_facts.json`; `03_valuation/value_driver_map.json`; `03_valuation/assumption_pack.md` | base margin; forecast margin; gross margin or EBIT margin; margin drivers; driver impacts if available | Explain what bridges current margin to forecast margin without changing assumptions. |
| `scenario_comparison` | Scenario comparison | `03_valuation/assumption_pack.md`; `03_valuation/valuation_state.json`; `03_valuation/valuation_analysis.md` | Bear/Base/Bull assumptions; revenue; EBIT or FCF; equity value or price target by scenario | Compare valuation and operating outcomes across Task 3 scenarios. |
| `dcf_sensitivity` | DCF sensitivity | `03_valuation/dcf_model.xlsx`; `03_valuation/valuation_state.json`; `03_valuation/valuation_analysis.md` | sensitivity row variable; sensitivity column variable; price per share or equity value matrix; base case marker | Show valuation sensitivity to key DCF assumptions exactly as Task 3 produced it. |
| `valuation_football_field` | Valuation football field | `03_valuation/valuation_state.json`; `03_valuation/valuation_analysis.md` | valuation methods; low/base/high values; current price if present; target price; method weights if present | Summarize valuation range by method and reconcile target price visually. |
| `comps_multiple_comparison` | Comps multiple comparison | `03_valuation/comps.xlsx`; `03_valuation/valuation_analysis.md`; `03_valuation/valuation_state.json` | peer names; relevant multiples; median/percentile; company multiple; premium/discount if provided | Show relative valuation versus the peer set used by Task 3. |
| `historical_valuation_multiples` | Historical valuation multiples | `03_valuation/valuation_analysis.md`; `03_valuation/valuation_state.json`; Task 3 historical multiple workbook if produced | dates or periods; historical multiple values; current multiple; long-term average or range if provided | Show where current valuation sits versus historical Task 3 sanity checks. |
| `catalyst_timeline` | Catalyst timeline | `01_company_research/business_driver_map.json`; `01_company_research/company_research.md`; `03_valuation/valuation_analysis.md` | catalyst name; expected date or period; impacted value driver; thesis impact | Show upcoming events that can confirm or disprove the investment thesis. |
| `risk_matrix` | Risk matrix | `01_company_research/company_research.md`; `01_company_research/business_driver_map.json`; `03_valuation/assumption_audit.md` | risk name; category; likelihood; impact; affected value driver; mitigation or monitoring item if available | Show the key risks, severity, and model or thesis linkage. |

## Allowed Calculations

Allowed chart transformations:

- Unit conversion using units stated in source artifacts.
- Percent of total.
- Year-over-year growth.
- CAGR where start and end values are both present.
- Common-size margin calculations from revenue and profit or cash flow lines.
- Sorting, indexing, and peer percentile placement.
- Labels that identify historical versus forecast periods.

Record each calculated field in `chart_index.json`. Do not use calculations to
create a new valuation conclusion.

## Output Contract

Write only Task 4 outputs under:

```text
04_charts/
  chart_pack/
  chart_index.json
```

Recommended chart filenames:

```text
chart_pack/revenue_by_segment.png
chart_pack/revenue_ebit_fcf_trend.png
chart_pack/margin_bridge.png
chart_pack/scenario_comparison.png
chart_pack/dcf_sensitivity.png
chart_pack/valuation_football_field.png
chart_pack/comps_multiple_comparison.png
chart_pack/historical_valuation_multiples.png
chart_pack/catalyst_timeline.png
chart_pack/risk_matrix.png
```

PNG is the default report-ready format. SVG and CSV chart data extracts may be
added when useful for auditability or downstream document assembly, but do not
replace the PNG chart files.

## chart_index.json Schema

`chart_index.json` must include the source artifact, data fields, and chart
purpose for every chart.

Use this minimum schema:

```json
{
  "task": "task4_chart_pack",
  "run_dir": "out/coverage/{market}-{ticker}/runs/{run_id}",
  "generated_at": "YYYY-MM-DDTHH:MM:SS",
  "source_artifacts": [
    "01_company_research/company_research.md",
    "01_company_research/business_driver_map.json",
    "01_company_research/source_log.json",
    "02_financial_model/integrated_model.xlsx",
    "02_financial_model/financial_facts.json",
    "03_valuation/dcf_model.xlsx",
    "03_valuation/comps.xlsx",
    "03_valuation/valuation_analysis.md",
    "03_valuation/valuation_state.json"
  ],
  "charts": [
    {
      "id": "revenue_by_segment",
      "title": "Revenue by Segment",
      "file": "chart_pack/revenue_by_segment.png",
      "format": "png",
      "source_artifacts": [
        "02_financial_model/financial_facts.json",
        "02_financial_model/integrated_model.xlsx"
      ],
      "data_fields": [
        "fiscal_year",
        "segment_revenue.history",
        "segment_revenue.forecast",
        "total_revenue"
      ],
      "calculated_fields": [
        "segment_percent_of_total"
      ],
      "chart_purpose": "Show revenue mix, segment contribution, and forecast mix shift.",
      "report_section": "Financial Performance",
      "missing_data_flags": []
    }
  ]
}
```

If a required chart cannot be created because Task 1-3 did not provide the
needed data, do not fabricate a file. Return a blocking dependency report and
include the missing artifact path and missing field name.

## Workflow

1. Verify the active run directory and required Task 1-3 artifacts.
2. Build a chart data map from structured artifacts first:
   `financial_facts.json`, `valuation_state.json`, Excel workbooks, then
   markdown prose where structured fields are unavailable.
3. Confirm the mandatory chart inventory can be sourced from Task 1-3 artifacts.
4. Generate charts in a consistent institutional style:
   clear title, unit labels, source note, fiscal-year axis, historical/forecast
   distinction, readable legend, and restrained colors.
5. Save chart files to `04_charts/chart_pack/`.
6. Write `04_charts/chart_index.json`.
7. Validate that every required chart has an index entry and that every indexed
   file exists.

## Quality Gates

Before completion:

- Confirm that no new research or external data was used.
- Confirm that Task 3 valuation conclusions are unchanged.
- Confirm every required chart is sourced to Task 1-3 artifacts.
- Confirm every `chart_index.json` chart entry has `source_artifacts`,
  `data_fields`, and `chart_purpose`.
- Confirm Task 5 can embed charts using paths relative to `04_charts/`.
