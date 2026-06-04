---
name: xlsx-author
description: Create Task 2 .xlsx workbook artifacts on disk in headless single-stock coverage runs.
---

# xlsx-author

Use this skill when the agent is running headless and must produce an Excel workbook file artifact rather than editing a live Excel session.

## Output Contract

- Write Task 2 workbooks under `02_financial_model/`.
- The required Task 2 workbook filename is `02_financial_model/integrated_model.xlsx`.
- Create directories if they do not exist.
- Return the workbook path to the orchestrator and make sure it is listed in the final Task 2 artifact index.

## Workbook Construction

Use `openpyxl` or the repository's deterministic Excel tooling. Build the workbook from normalized facts and assumptions, not from precomputed Python outputs.

Formula cells must be written as Excel formulas:

```python
ws["D15"] = "=D14*(1+Assumptions!D8)"
```

Do not write the calculated answer into a projection or subtotal cell:

```python
# Wrong for projection cells
ws["D15"] = 12500
```

## Formatting Conventions

Use a restrained financial-model style unless a template overrides it:

- Blue font: hardcoded inputs and historical actuals.
- Black font: formulas.
- Green font: cross-sheet links.
- Dark blue fill with white bold font: major section headers.
- Light blue fill with bold font: period headers and check rows.
- Grey fill: input areas where helpful.

## Required Workbook Features

- All tabs required by `three-statement-model`.
- Named ranges or clearly labeled output cells for values consumed by reports, charts, or Task 3.
- `Sources` tab linking source IDs to inputs.
- `Checks` tab with BS balance, cash tie-out, NI link, RE roll-forward, CapEx/PP&E tie, and debt tie.
- `DCF Inputs` tab pulling from model outputs with formulas.

## Recalculation and Validation

- Set workbook calculation mode to automatic when supported.
- Open/recalculate with the available local spreadsheet engine if the repository provides one.
- Always run `audit-xls` after creating or updating any Excel artifact.

## Prohibited Patterns

- Do not append Task 2 output into an unrelated workbook unless explicitly requested.
- Do not hide failed checks.
- Do not convert linked projection formulas to static values.
- Do not leave `DCF Inputs` as manually copied numbers.
