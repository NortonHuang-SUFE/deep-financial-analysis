# Single Stock Coverage Agent

LangGraph Deep Agents workflow for single-stock equity coverage.

This project implements the root-level `single-stock-coverage-plan.md`:

- Task 1: Company Research
- Task 2: Financial Modeling
- Task 3: Valuation Analysis
- Task 4: Chart Generation
- Task 5: Report Assembly

The graph entry is `single_stock_coverage` in `langgraph.json`.

Artifacts are written under workspace-level `coverage/{market}-{ticker}/runs/<timestamp>/`.
