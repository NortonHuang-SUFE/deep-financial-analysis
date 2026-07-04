# Changelog

## v0.5.0 daily-report-preview

- 破坏性瘦身：公开 LangGraph graph 收敛为 `daily_report`。
- 删除旧投研能力：DCF、个股覆盖、行业研究、股票筛选、thesis tracker 和独立 market research。
- 保留日报链路：`daily_report` 只协调 `morning_note` 与 `html_image_renderer`。
- 清理根配置：`langgraph.json`、`model-routing.yaml`、`tool-concurrency.yaml` 只保留日报、渲染和协调器所需配置。
- 增加本地 / 内网 Docker 支持：LangGraph Dockerfile 安装 Chromium 和中文字体，renderer 默认使用 `/usr/bin/chromium`。
