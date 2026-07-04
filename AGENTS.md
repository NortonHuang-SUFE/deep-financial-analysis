# Repository Guidelines

## Build, Test, and Development Commands

Run the LangGraph development server with `.venv/bin/langgraph dev`. Open the model configuration UI with `.venv/bin/python -m financial_agent_runtime.model_admin`.

## Coding Style & Naming Conventions

Use standard Python style: four-space indentation, snake_case modules/functions, PascalCase classes, and explicit type-friendly interfaces where practical. Keep package code under each package's `src/<package_name>/` directory. Prefer existing runtime helpers from `financial-agent-runtime` over duplicating MCP, model routing, concurrency, or filesystem behavior. `ruff` is the project linting tool where configured; run it per package when editing Python code.

## Testing Guidelines

Tests use `pytest` and, for async graph behavior, `pytest-asyncio`. Test files follow `tests/test_*.py`. Run focused tests from the repository root, for example:

```bash
.venv/bin/python -m pytest financial-agent-runtime/tests
.venv/bin/python -m pytest morning-note/tests html-image-renderer/tests orchestrator/tests
```

Add tests beside the package you change, especially for config parsing, graph wiring, tool access, and artifact path behavior.

## Commit & Pull Request Guidelines

Recent history uses concise conventional-style subjects such as `feat: ...`, `fix: ...`, and `docs: ...`; keep commits scoped and imperative. Pull requests should include a short purpose statement, affected packages, test commands run, linked issues when available, and screenshots or sample artifact paths for visual/report changes.

Before creating any pull request, ask the user whether the release should be a small version bump or a major version bump. For a small version bump, update only the third segment of the `x.x.x` version number. For a major version bump, ask the user to specify the exact target version number before editing version metadata. Every pull request must update the changelog; major version pull requests must also update the README.

## Security & Configuration Tips

Copy `.env.example` to `.env` for local secrets. Never commit API keys, MCP tokens, or generated private artifacts. Keep public routing and concurrency settings in `model-routing.yaml` and `tool-concurrency.yaml`; store secret values only in environment variables.
