# Changelog

## v0.1.1 - 2026-07-09

- Added a Vite / React LangGraph Console frontend for connecting to `daily_report`, submitting runs, and inspecting main-agent, subagent, tool-call, and event streams.
- Docker deployment config now copies `model-routing.yaml` and `tool-concurrency.yaml` into `/deps` so model routing and tool concurrency settings are available in the container.
- Added MiniMax, DashScope DeepSeek, and Qwen model profiles, and fixed the `minimax-m3` profile references.
- Python subpackages now depend on the released `financial-agent-runtime>=0.1.1` while keeping local `uv` editable sources for development.
- The coordinator prompt now requires the final reply and `daily-report-summary.md` to return a complete artifact index with all artifact paths, not only key paths.

## v0.1.0 - 2026-07-04

- Initial release: a focused China-market daily report agent.
- Public LangGraph graph is `daily_report`, coordinating report generation and visual rendering.
- Internal capabilities are `morning_note` and `html_image_renderer`.
- Root configuration includes `langgraph.json`, `model-routing.yaml`, `tool-concurrency.yaml`, and `.env.example`.
- Local / intranet Docker deployment support: the LangGraph Dockerfile installs Chromium and CJK fonts, and the renderer defaults to `/usr/bin/chromium`.
- Tests cover retained packages, graph exposure, orchestrator subagent registration, cleaned configuration, and container browser fallback.
