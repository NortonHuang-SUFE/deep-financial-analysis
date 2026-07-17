# Changelog

## v0.1.3 - 2026-07-16

- 新增国泰海通融资融券公众号专用长图 Skill，包含自适应高度规范、品牌 Logo、二维码、合规声明和完整示例资产。
- 修正 HTML 远程资源校验，允许内嵌 `data:` 资源，并新增两融长图 Skill 合约与资产覆盖测试。
- 将 HTML 图片渲染器的默认模型切换为 `aliyun-minimax-m3`，同时保留 `minimax-m3` 作为多模态回退模型。

## v0.1.2 - 2026-07-13

- 新增 DashScope `glm-5.2` 和 `glm-5.2-fast-preview` 模型 profile，并将日报与早报的默认模型切换为 `aliyun-glm-5.2-fast`。
- 简化模型路由配置，移除各 profile 中重复的 `max_tokens` 和 `thinking` 字段。
- 调度器现在为每个视觉产物预分配独立的 slot 目录，支持安全地并行生成 PC、移动端等多个图片变体。
- 新增调度器提示词与运行时上下文测试，防止多个渲染任务共用输出目录或返回重复产物路径。

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
