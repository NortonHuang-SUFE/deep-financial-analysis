# Changelog

## v0.1.5 - 2026-07-24

- 将融资融券微信富文本改为移动端优先布局，并新增 375px、320px 两档自动检查，覆盖横向裁切、表头换行、字号、图片缩放和容器留白。
- 强制 HTML 渲染任务交付同序号长图 HTML、PNG 和微信富文本三件套；调度器会核对 companion artifact，并在缺失时重试或明确报告失败。
- 将运行时上下文统一为每次 graph 调用只生成一次的共享中间件，避免时间戳变化破坏模型前缀缓存，同时保持并发运行相互隔离。
- 补充 DashScope 与火山方舟 GLM 的 thinking 参数映射，并将早报和 HTML 渲染器切换到关闭 thinking 的 `aliyun-glm-5.2`。

## v0.1.4 - 2026-07-22

- 完善融资融券微信公众号富文本渲染流程，新增独立富文本示例、自动校验脚本和更严格的渲染器测试覆盖。
- 更新国泰海通品牌 Logo 与二维码资产，并精简示例长图结构以适配公众号内容发布。
- 新增 DashScope Kimi K3 模型 profile 与 `reasoning_effort` 路由配置，并将日报和 HTML 图片渲染器默认模型切换为 Kimi K3。
- 移除不再使用的 Vite / React 前端及相关忽略规则，缩减仓库维护范围。

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
