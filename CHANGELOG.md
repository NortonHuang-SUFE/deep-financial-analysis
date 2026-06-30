# 更新日志

本文件记录 `Deep Financial Analysis` 的版本历史。English version: [CHANGELOG.en.md](CHANGELOG.en.md)。项目说明见 [README.md](README.md)。

## v0.3.0 - 2026-06-30

- 新增「外部工具并发限制」：在工作区根目录的 `tool-concurrency.yaml` 中定义 `groups`，每个 group 是一个进程级共享并发配额；当组内在途调用数达到 `max_concurrency`，后续调用（跨该组所有工具、跨所有 agent/subagent）排队串行执行，直到有空位释放。
- 配置方式：工具通过两种 glob 入组——`mcp_servers`（匹配 MCP server 名，如 `ifind-*`）或 `tools`（匹配工具 `.name`，如 `web_search`）；一个工具命中多个 group 时取最严（`max_concurrency` 最小者）。可在该文件里改阈值、加 group，或把多个具名工具/server 归入同一 group 共享配额。
- 默认配置：`ifind` 组把所有 `ifind-*` server 归为一个配额（`max_concurrency: 2`），避免 orchestrator 并行派发多个子 agent 时打爆同花顺 iFind。
- 路径与开关：可用环境变量 `TOOL_CONCURRENCY_CONFIG` 覆盖配置文件路径；文件不存在则不做任何限制（功能为 no-op）。改动在下次 graph 加载时生效（重启 `langgraph dev`）。
- 抽出共享运行时模块 `financial_agent_runtime.concurrency`，导出 `load_and_register_mcp_tools`、`make_concurrency_limit_middleware`、`load_tool_concurrency_config`、`register_limited_tools`、`resolve_tool_group`；统一各 agent 的 MCP 工具加载，并把并发限制中间件接入全部 7 个顶层 agent 的 graph。
- 新增 `financial-agent-runtime/tests/test_concurrency.py` 回归测试：覆盖配置解析、环境变量覆盖、glob 匹配与多组取最严、以及 sync/async 中间件的限流行为。

## v0.2.0 - 2026-06-28

- 新增云端运行模式：通过 `AGENT_BACKEND=daytona` 让全部 agent 在临时 Daytona 云端沙箱内执行与落盘；默认仍为 `local` 本地模式，两种模式共用同一套 agent 代码。
- 抽出共享运行时包 `financial-agent-runtime`，统一后端选择、产物存储根、skills 同步、产物写入和 general-purpose subagent 禁用逻辑，消除各子 agent 的重复实现。
- `.env.example` 增加 `AGENT_BACKEND`、`DAYTONA_*` 凭证和 `DAYTONA_FILE_STORAGE_ROOT` 说明（中英文注释）。
- 安装说明补充 `financial-agent-runtime` 共享包；`langgraph.json` 将其登记为首个依赖。
- 新增针对云端/本地后端与产物路径的回归测试。

## v0.1.1 - 2026-06-25

- 统一 orchestrator 与子 agent 的产物目录协议：一次复合任务只固定一个母文件夹，所有子 agent 产物递归嵌套在该目录下。
- 支持上游传入的 `output_dir` 精确落盘；`morning_note`、`stock_screen`、`sector_research`、`thesis_tracker` 和 `market_researcher` 不再在已分配任务目录下额外创建第二层时间戳目录。
- 更新 `html_image_renderer` 的协作规则：由 orchestrator 调度时直接在指定子目录下写入 `html/` 和 `png/`。
- 同步更新已挂载 skill 文档，避免 skill 指令继续要求创建新的顶层 `out/<timestamp>/`。
- 增加针对 artifact root / output directory 行为的回归测试。

## v0.1.0 - 2026-06-21

- 初始 research-preview：接入核心投研 agent、同花顺 iFind MCP、本地 artifacts 输出、三表模型、DCF、图表包和 HTML 图片渲染。
