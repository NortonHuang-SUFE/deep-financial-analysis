# Changelog

## v0.1.1 - 2026-07-09

- 新增 Vite / React LangGraph Console 前端，用于连接 `daily_report`、提交运行请求，并查看主 agent、subagent、tool call 与事件流。
- Docker 部署配置会把 `model-routing.yaml` 和 `tool-concurrency.yaml` 一并复制进 `/deps`，保证容器内模型路由和工具并发配置可用。
- 模型路由新增 MiniMax、DashScope DeepSeek 和 Qwen profile，并修正 `minimax-m3` profile 引用。
- Python 子包改用发布版 `financial-agent-runtime>=0.1.1` 依赖，同时保留本地 `uv` editable source 便于开发。
- 调度器提示词强制最终回复和 `daily-report-summary.md` 返回完整 artifact index，即所有产物地址，而不是只返回关键路径。

## v0.1.0 - 2026-07-04

- 初始版本：项目定位为面向中国二级市场的日报 Agent。
- 公开 LangGraph graph 为 `daily_report`，用于协调日报生成和视觉渲染。
- 内部能力包括 `morning_note` 和 `html_image_renderer`。
- 根配置包括 `langgraph.json`、`model-routing.yaml`、`tool-concurrency.yaml` 和 `.env.example`。
- 本地 / 内网 Docker 部署支持：LangGraph Dockerfile 安装 Chromium 和中文字体，renderer 默认使用 `/usr/bin/chromium`。
- 测试覆盖保留包、graph 暴露、orchestrator subagent 注册、配置清理和容器浏览器路径。
