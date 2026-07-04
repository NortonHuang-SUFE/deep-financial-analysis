# Changelog

## v0.1.0 - 2026-07-04

- Initial release: a focused China-market daily report agent.
- Public LangGraph graph is `daily_report`, coordinating report generation and visual rendering.
- Internal capabilities are `morning_note` and `html_image_renderer`.
- Root configuration includes `langgraph.json`, `model-routing.yaml`, `tool-concurrency.yaml`, and `.env.example`.
- Local / intranet Docker deployment support: the LangGraph Dockerfile installs Chromium and CJK fonts, and the renderer defaults to `/usr/bin/chromium`.
- Tests cover retained packages, graph exposure, orchestrator subagent registration, cleaned configuration, and container browser fallback.
