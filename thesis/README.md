# Thesis Tracker Agent

`thesis/` 是一个独立的 LangGraph Deep Agents 项目，用于维护 A 股和港股个股投资逻辑、更新 thesis scorecard，并输出可复盘的 markdown 与 JSON artifact。

## 配置

模型 profile 与 agent 绑定统一在 workspace 根目录 `model-routing.yaml` 配置；MCP URL、工具授权和输出配置统一在根目录 `tool-concurrency.yaml` 配置。密钥从 workspace 根目录 `.env` 读取，也就是 `financialServicesModified/.env`，不需要在 `thesis/` 内放 `.env`。

常用环境变量：

```bash
DASHSCOPE_API_KEY=...
MINIMAX_API_KEY=...
ARK_API_KEY=...

IFIND_MCP_TOKEN=...
# 或
IFIND_MCP_AUTHORIZATION="Bearer ..."
MX_DS_MCP_API_KEY=...
```

iFind 鉴权只支持全局共享 key；单 server 可覆盖 URL/transport，例如：

```bash
IFIND_STOCK_MCP_URL=https://example.test/mcp
IFIND_STOCK_MCP_TRANSPORT=streamable_http
MX_DS_MCP_URL=https://mxapi.eastmoney.com/mxds/mcp
MX_DS_MCP_TRANSPORT=streamable-http
```

`mx-ds-mcp` 随已有 iFind MCP 配置一起启用。可用根目录
`tool-concurrency.yaml` 的 `tool_groups` / `agent_tools` 收窄本 agent 可用的
MCP server。

调试开关：

```bash
THESIS_TRACKER_TEST_MODE=1
THESIS_TRACKER_DISABLE_MCP=1
THESIS_TRACKER_OUTPUT_TIMESTAMP=20260602-120000
```

## 运行

从 `thesis/` 目录运行 LangGraph：

```bash
cd thesis
../.venv/bin/langgraph dev
```

`langgraph.json` 暴露 graph 名称 `thesis_tracker`，入口为 `./src/thesis_tracker_agent/graph.py:graph`，并加载 `../.env`。

## 输出

本地工具会写入 workspace 根目录：

```text
out/<YYYYMMDD-HHMMSS>/
```

同一次进程任务会复用同一个时间戳目录。可以设置 `THESIS_TRACKER_OUTPUT_TIMESTAMP` 固定目录名，便于测试和复现。

可用本地工具：

- `create_task_output_dir`
- `write_markdown_report`
- `write_json_artifact`

## 测试

```bash
../.venv/bin/python -m pytest tests
```

也可以从 workspace 根目录运行：

```bash
.venv/bin/python -m pytest thesis/tests
```
