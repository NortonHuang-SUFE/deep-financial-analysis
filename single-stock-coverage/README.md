# Single Stock Coverage Agent

LangGraph Deep Agents workflow for single-stock equity coverage.

This project implements the root-level `single-stock-coverage-plan.md`:

- Task 1: Company Research
- Task 2: Financial Modeling
- Task 3: Valuation Analysis
- Task 4: Chart Generation
- Task 5: Report Assembly

The graph entry is `single_stock_coverage` in `langgraph.json`. Agent wiring
for prompts, tool groups, skills, and nested subagents lives in
`agents/registry.yaml`; the root `langgraph.json` also exposes each task and
nested task graph for direct debugging.

Task 2 uses a context-controlled statement workflow:

- `task2_financial_modeler` prepares `financial_facts.json` and a compact
  `task2_context_packet.json`.
- `is_modeler`, `bs_modeler`, and `cf_modeler` run as independent statement
  JSON workers. They each have statement-specific tools and write only their
  own JSON artifacts.
- The Task 2 parent reconciles the three statement JSON files with
  `reconcile_statement_specs`, builds `integrated_model.xlsx` with deterministic
  builder tools, and gates Task 3 handoff with workbook validation and
  `audit-xls` checks.

Artifacts are written under workspace-level `coverage/{market}-{ticker}/runs/<timestamp>/`.
