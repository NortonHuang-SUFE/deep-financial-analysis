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

- `task2_financial_modeler` is a parent coordinator for assignment,
  reconciliation checks, manifest updates, and Task 3 handoff gates.
- `is_modeler`, `bs_modeler`, and `cf_modeler` run as independent statement
  JSON workers. They use MCP data for their own statements, apply
  financial-data normalization, and write only their own JSON artifacts.
- The Task 2 parent reconciles the three statement JSON files with
  `reconcile_statement_specs`; this also writes `financial_facts.json` and
  `task2_context_packet.json`.
- `workbook_builder` is the only Task 2 child that builds
  `integrated_model.xlsx`, validates the workbook, and writes `model_audit.md`.
- `model_update_executor` refreshes an existing workbook from reconciled
  statement specs without using MCP tools.

Artifacts are written under workspace-level `out/coverage/{market}-{ticker}/runs/<timestamp>/`.
