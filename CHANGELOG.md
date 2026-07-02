# 更新日志

本文件记录 `Deep Financial Analysis` 的版本历史。English version: [CHANGELOG.en.md](CHANGELOG.en.md)。项目说明见 [README.md](README.md)。

## v0.4.1 - 2026-07-02

- 新增模型路由的多模态兜底配置：`model-routing.yaml` 支持根级 `default_multimodal_model`，也支持每个 agent/subagent 通过 `agent_models.<name>.multimodal_fallback_model` 单独覆盖。
- 更新 `financial_agent_runtime.build_chat_model_for_agent`：当配置了兜底模型且不同于主模型时，返回带 fallback 的 ChatModel 包装器，并保持工具绑定后的 fallback 行为。
- 更新本地模型配置管理页，可编辑默认多模态兜底模型和每个 agent/subagent 的兜底模型绑定。
- 扩展 `model-routing.yaml` 默认配置和模型路由回归测试，覆盖字符串式旧配置、结构化 agent route、默认兜底、agent 级覆盖、未知 profile 报错和保存时省略空字段。

## v0.4.0 - 2026-07-02

- 新增根级模型路由配置：`model-routing.yaml` 统一保存模型 profile、`api_key_env` 变量名、默认模型和每个 agent/subagent 的模型绑定；真实密钥仍只放在 `.env` 或进程环境变量中。
- 新增本地模型配置管理页：通过 `.venv/bin/python -m financial_agent_runtime.model_admin` 打开 `http://127.0.0.1:8765`，可编辑模型 profile、密钥环境变量名和 agent/subagent 绑定，并写回根目录 `model-routing.yaml`。
- 新增根级工具授权配置：`tool-concurrency.yaml` 现在同时承载 MCP endpoint、agent runtime 默认值、工具组、agent/subagent 工具授权和外部工具并发限制，移除各子项目分散的 `config.yaml` 配置入口。
- 新增 `financial_agent_runtime.model_routing` 与 `financial_agent_runtime.tool_access` 共享模块，统一 ChatOpenAI 模型构建、OpenAI-compatible gateway 校验、工具目录构建、工具组解析和 agent/subagent 工具可见性控制。
- 更新所有顶层 agent、DCF 子 agent 和 single-stock coverage 内部 subagent 的图构建逻辑，统一从根级模型路由与工具授权配置解析模型、MCP、本地工具、搜索工具和输出目录。
- 新增模型路由、工具授权和 graph 配置回归测试，覆盖旧配置迁移、agent/subagent 模型解析、工具组授权、MCP 访问和测试模式下的配置暴露。

## v0.3.2 - 2026-07-01

- 收紧 `single-stock-coverage` 根 orchestrator 权限：新增 `coverage_orchestration_tools`，根 agent 仅保留创建 coverage run、更新 manifest 和写 coverage state 的编排工具，不再直接持有业务 artifact 写入工具。
- 禁用根 agent 的通用 `write_file`、`edit_file`、`execute` 内置工具，并在根 prompt 中明确要求 Task 1-5 业务产物必须由对应 task subagent 写入；缺失或质量不足时应重跑对应 child 或报告 blocker，不再由根 agent 补 placeholder。
- 强化 `run_manifest.json` 完成态校验：顶层任务标记为 `completed` 时，必须同时满足对应 subagent 已记录在 `subagents_called` 中，且该任务必需产物已真实存在于 run directory 下；否则 `update_run_manifest` 会返回结构化失败。
- 新增回归测试覆盖非法完成态拒绝、Task 2 简化产物拒绝、根 agent 工具组/内置工具排除配置，以及 graph test mode 下的 registry 配置暴露。

## v0.3.1 - 2026-06-30

- 修复模型网关 `base_url` 处理：新增共享函数 `financial_agent_runtime.normalize_openai_compatible_base_url`，仅在 URL 未显式带 API 版本段时才补 `/v1`；已显式带版本的网关（如火山方舟 `…/api/v3`）保持原样，避免被错误地拼成 `/api/v3/v1`，同时仍兼容只填到域名的 DashScope `compatible-mode` 等场景。
- 全部 9 个 agent 的 `graph.py` 统一改用该共享函数，替换原先各自内联的 `base_url.rstrip("/")`，消除重复逻辑。
- 新增火山方舟（Volcengine Ark）凭证识别：当网关指向 `volces.com` / `volcengineapi.com` 时，按序回退读取 `ARK_API_KEY`、`VOLCENGINE_API_KEY`、`VOLCENGINE_ARK_API_KEY`；缺失 key 的报错信息补充提示可使用 `DASHSCOPE_API_KEY`、`ARK_API_KEY` 等供应商专用 key。
- `.env.example` 补充 `ARK_API_KEY` 说明与火山方舟网关示例。
- 新增 `normalize_openai_compatible_base_url` 的回归测试，覆盖补 `/v1`、保留显式 `/v1`、保留 `/api/v3` 与本地端点等情况。

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
