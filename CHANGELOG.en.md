# Changelog

## v0.5.0 daily-report-preview

- Breaking slimdown: the public LangGraph graph is now only `daily_report`.
- Removed legacy research capabilities: DCF, single-stock coverage, sector research, stock screening, thesis tracking, and standalone market research.
- Kept the daily-report workflow: `daily_report` coordinates only `morning_note` and `html_image_renderer`.
- Cleaned root configuration so `langgraph.json`, `model-routing.yaml`, and `tool-concurrency.yaml` only contain daily-report, renderer, and coordinator settings.
- Added local / intranet Docker support: the LangGraph Dockerfile installs Chromium and CJK fonts, and the renderer defaults to `/usr/bin/chromium`.
