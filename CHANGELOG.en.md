# Changelog

## v0.1.5 - 2026-07-28

- Made margin-trading WeChat rich text mobile-first and added automated checks at 375px and 320px for clipping, wrapped headers, font size, image scaling, and container padding.
- Required every HTML rendering run to deliver same-sequence long-image HTML, PNG, and WeChat rich text; the orchestrator now reconciles companion artifacts and retries or reports missing output explicitly.
- Centralized runtime context in a shared once-per-graph-invocation middleware and added a first-value-wins reducer for concurrent writes in one superstep, preventing prefix-cache churn and `InvalidUpdateError` failures.
- Required morning-note to finish and return its actual artifact paths before HTML rendering starts, while still allowing multiple renderers to run in parallel afterward.
- Added provider-specific thinking mappings for DashScope and Volcengine GLM models, moved daily-report and morning-note to `volcengine-glm-5.2-plan`, and selected `aliyun-minimax-m3` for HTML rendering with a MiniMax fallback.

## v0.1.4 - 2026-07-22

- Improved the margin-trading WeChat rich-text rendering workflow with a standalone rich-text example, an automated validator, and stricter renderer test coverage.
- Refreshed the GTJA logo and QR-code assets, and simplified the example long-image structure for WeChat publishing.
- Added a DashScope Kimi K3 model profile and `reasoning_effort` routing support, and switched the daily-report and HTML image renderer defaults to Kimi K3.
- Removed the unused Vite / React frontend and its related ignore rules to reduce the repository maintenance surface.

## v0.1.3 - 2026-07-16

- Added a dedicated GTJA margin-trading WeChat long-image skill with adaptive-height guidance, branded logo and QR assets, compliance notices, and a complete example.
- Fixed HTML remote-resource validation to allow embedded `data:` resources, and added contract and asset coverage for the margin-trading skill.
- Switched the HTML image renderer default model to `aliyun-minimax-m3`, retaining `minimax-m3` as the multimodal fallback.

## v0.1.2 - 2026-07-13

- Added DashScope `glm-5.2` and `glm-5.2-fast-preview` model profiles, and switched the daily-report and morning-note defaults to `aliyun-glm-5.2-fast`.
- Simplified model routing by removing repeated `max_tokens` and `thinking` fields from individual profiles.
- The coordinator now pre-assigns an exclusive slot directory to each visual artifact, allowing PC, mobile, and other image variants to render safely in parallel.
- Added coordinator prompt and runtime-context coverage to prevent renderer tasks from sharing output directories or returning duplicate artifact paths.

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
