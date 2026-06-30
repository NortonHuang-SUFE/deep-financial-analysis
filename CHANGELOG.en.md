# Changelog

Version history for `Deep Financial Analysis`. 中文版本：[CHANGELOG.md](CHANGELOG.md)。Project overview: [README.en.md](README.en.md).

## v0.3.0 - 2026-06-30

- Added external-tool concurrency limits: define `groups` in `tool-concurrency.yaml` at the workspace root. Each group is one shared, process-wide budget; when in-flight calls in a group reach `max_concurrency`, further calls (across all tools in that group, across all agents/subagents) queue and run serially until a slot frees.
- Configuration: a tool joins a group by matching either a `mcp_servers` glob (against the MCP server name, e.g. `ifind-*`) or a `tools` glob (against the tool `.name`, e.g. `web_search`); if a tool matches more than one group, the most restrictive (smallest `max_concurrency`) wins. Edit thresholds, add groups, or pull multiple named tools/servers into one shared budget.
- Default config: the `ifind` group treats every `ifind-*` server as one budget (`max_concurrency: 2`), so an orchestrator fanning out to many subagents will not overwhelm Tonghuashun iFind.
- Path and toggle: override the config path with the `TOOL_CONCURRENCY_CONFIG` env var; if the file is absent, nothing is limited (the feature is a no-op). Changes take effect on the next graph load (restart `langgraph dev`).
- Extracted a shared runtime module `financial_agent_runtime.concurrency` exporting `load_and_register_mcp_tools`, `make_concurrency_limit_middleware`, `load_tool_concurrency_config`, `register_limited_tools`, and `resolve_tool_group`; unified MCP tool loading across agents and wired the concurrency-limit middleware into all 7 top-level agent graphs.
- Added `financial-agent-runtime/tests/test_concurrency.py` regression coverage: config parsing, env-var override, glob matching and multi-group tie-breaking, and sync/async middleware throttling.

## v0.2.0 - 2026-06-28

- Added a cloud run mode: with `AGENT_BACKEND=daytona`, all agents execute and persist artifacts inside an ephemeral Daytona cloud sandbox; the default stays `local`, and both modes share one agent codebase.
- Extracted a shared `financial-agent-runtime` package that centralizes backend selection, artifact storage root, skills mirroring, artifact writes, and general-purpose subagent disabling, removing the duplicated per-agent implementations.
- `.env.example` documents `AGENT_BACKEND`, `DAYTONA_*` credentials, and `DAYTONA_FILE_STORAGE_ROOT` (bilingual comments).
- Install instructions now include the shared `financial-agent-runtime` package; `langgraph.json` registers it as the first dependency.
- Added regression tests for the cloud/local backends and artifact paths.

## v0.1.1 - 2026-06-25

- Unified the artifact directory contract between the orchestrator and subagents: each composite run now uses one mother folder, with all subagent outputs nested recursively underneath it.
- Made upstream `output_dir` values exact task directories for `morning_note`, `stock_screen`, `sector_research`, `thesis_tracker`, and `market_researcher`, avoiding accidental second-level timestamp folders.
- Updated `html_image_renderer` orchestration rules so it writes `html/` and `png/` directly under the assigned renderer subdirectory.
- Synchronized mounted skill documentation so skills no longer instruct agents to create a separate top-level `out/<timestamp>` directory during orchestrated runs.
- Added regression coverage for artifact root / output directory behavior.

## v0.1.0 - 2026-06-21

- Initial research-preview with core research agents, Tonghuashun iFind MCP access, local artifact output, three-statement modeling, DCF, chart packs, and HTML image rendering.
