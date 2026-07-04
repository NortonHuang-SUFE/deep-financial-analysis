# Changelog

## v0.1.0 - 2026-07-04

- 初始版本：项目定位为面向中国二级市场的日报 Agent。
- 公开 LangGraph graph 为 `daily_report`，用于协调日报生成和视觉渲染。
- 内部能力包括 `morning_note` 和 `html_image_renderer`。
- 根配置包括 `langgraph.json`、`model-routing.yaml`、`tool-concurrency.yaml` 和 `.env.example`。
- 本地 / 内网 Docker 部署支持：LangGraph Dockerfile 安装 Chromium 和中文字体，renderer 默认使用 `/usr/bin/chromium`。
- 测试覆盖保留包、graph 暴露、orchestrator subagent 注册、配置清理和容器浏览器路径。
