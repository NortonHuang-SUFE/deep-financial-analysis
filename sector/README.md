# Sector Research Agent

`sector/` 是一个独立的 LangGraph Deep Agents 中国行业研究项目，graph 名为 `sector_research`，Python 包名为 `sector_research_agent`。

## 配置

模型 profile 与 agent 绑定统一在 workspace 根目录 `model-routing.yaml` 配置；MCP URL、工具授权和输出配置统一在根目录 `tool-concurrency.yaml` 配置。

认证从 workspace 根目录 `.env` 读取，也就是 `financialServicesModified/.env`，不是 `sector/.env`。常用环境变量：

```bash
DASHSCOPE_API_KEY=...
MINIMAX_API_KEY=...
ARK_API_KEY=...
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=...
MX_DS_MCP_API_KEY=...
```

iFind 鉴权只支持共享 key；单 server 只允许覆盖 URL/transport，例如：

```bash
IFIND_EDB_MCP_URL=https://example.test/mcp
IFIND_EDB_MCP_TRANSPORT=streamable_http
MX_DS_MCP_URL=https://mxapi.eastmoney.com/mxds/mcp
MX_DS_MCP_TRANSPORT=streamable-http
```

## MCP

默认配置以下 iFind MCP：

- `ifind-stock`
- `ifind-fund`
- `ifind-edb`
- `ifind-news`
- `ifind-bond`
- `ifind-global-stock`
- `ifind-index`
- `mx-ds-mcp`

可用根目录 `tool-concurrency.yaml` 的 `tool_groups` / `agent_tools` 收窄本
agent 可用的 MCP server。

如需本地导入或测试时禁用 MCP：

```bash
SECTOR_RESEARCH_DISABLE_MCP=1
```

测试模式会让 `graph.py` 返回简单对象，便于导入测试：

```bash
SECTOR_RESEARCH_TEST_MODE=1
```

## 运行

从 `sector/` 目录启动：

```bash
langgraph dev
```

也可以用父级虚拟环境运行测试：

```bash
../.venv/bin/python -m pytest tests
```

## 输出

本地工具会写入 workspace 根目录：

```text
out/<YYYYMMDD-HHMMSS>/
```

同一次任务复用同一个时间戳目录。需要固定输出目录时设置：

```bash
SECTOR_RESEARCH_OUTPUT_TIMESTAMP=20260602-120000
```

Agent 至少提供三个本地工具：

- `create_task_output_dir`
- `write_markdown_report`
- `write_json_artifact`
