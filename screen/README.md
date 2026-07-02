# Stock Screen Agent

`screen/` 是一个独立的 LangGraph Deep Agents 项目，用于 A 股和港股股票筛选、主题扫描、风格因子筛选和多空风险提示。Graph 名称是 `stock_screen`，Python 包名是 `stock_screen_agent`。

## 配置

模型 profile 与 agent 绑定统一在 workspace 根目录 `model-routing.yaml` 配置；MCP URL、工具授权和输出配置统一在根目录 `tool-concurrency.yaml` 配置。

请在工作区根目录 `.env` 配置密钥，也就是 `screen/../.env`：

```bash
DASHSCOPE_API_KEY=
MINIMAX_API_KEY=
ARK_API_KEY=
IFIND_MCP_TOKEN=
# 或者直接传 Authorization 原文
IFIND_MCP_AUTHORIZATION=
MX_DS_MCP_API_KEY=
```

每个 iFind server 支持单独覆盖 URL/transport，但不支持单独 key：

```bash
IFIND_NEWS_MCP_URL=...
IFIND_NEWS_MCP_TRANSPORT=streamable_http
MX_DS_MCP_URL=https://mxapi.eastmoney.com/mxds/mcp
MX_DS_MCP_TRANSPORT=streamable-http
```

已配置的 MCP server 包括 `ifind-stock`、`ifind-fund`、`ifind-edb`、`ifind-news`、`ifind-bond`、`ifind-global-stock`、`ifind-index`、`mx-ds-mcp`。可用根目录 `tool-concurrency.yaml` 的 `tool_groups` / `agent_tools` 收窄本 agent 可用的 MCP server。

## 运行

从项目目录运行：

```bash
cd screen
../.venv/bin/langgraph dev
```

或从工作区根目录运行测试/导入时使用：

```bash
.venv/bin/python -m pytest screen/tests
```

测试或离线导入可设置：

```bash
STOCK_SCREEN_TEST_MODE=1
STOCK_SCREEN_DISABLE_MCP=1
```

## 输出

本地工具会写入工作区根目录：

```text
out/<YYYYMMDD-HHMMSS>/
```

同一次进程任务会复用同一个时间戳目录。需要固定目录时设置：

```bash
STOCK_SCREEN_OUTPUT_TIMESTAMP=20260602-150000
```

可用本地工具：

- `create_task_output_dir`: 创建或返回本次任务输出目录
- `write_markdown_report`: 写入 Markdown 筛选报告
- `write_json_artifact`: 写入 JSON 结构化结果

## 研究口径

Agent prompt 位于 `agents/screen.md`，技能位于 `skills/idea-generation/SKILL.md`。默认使用中文输出，优先使用 iFind 来源；无法来源化的数据必须标记为 `[UNSOURCED]`。筛选会显式考虑 A 股/港股市场规则，包括涨跌停、ST/退市风险、停复牌、限售解禁、北向/融资融券、财报季、交易日/节假日、监管问询和政策催化。
