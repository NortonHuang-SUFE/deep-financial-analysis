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

Artifacts are written under workspace-level `coverage/{market}-{ticker}/runs/<timestamp>/`.
