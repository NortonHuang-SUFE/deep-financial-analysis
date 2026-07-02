# Market Researcher

LangGraph Deep Agents 行业研究项目，入口是 `langgraph.json` 中的
`market_researcher` graph。

## 配置从哪里来

项目默认从 workspace 根目录读取配置和密钥：

- `../model-routing.yaml`：模型 profile 与 agent/subagent 绑定。
- `../tool-concurrency.yaml`：MCP endpoint、工具授权、搜索默认值和输出目录。
- `../.env`：本机密钥和临时覆盖项。

不要把真实 key 放进任何 YAML；真实 key 只放进 workspace 根目录 `.env`。

## 大模型调用

模型 profile 与 agent/subagent 绑定统一在 workspace 根目录
`model-routing.yaml` 配置；`.env` 只保存 `api_key_env` 指向的真实密钥：

```bash
DASHSCOPE_API_KEY=...
MINIMAX_API_KEY=...
ARK_API_KEY=...
```

可用本地配置页编辑模型 profile 与 agent/subagent 绑定：

```bash
.venv/bin/python -m financial_agent_runtime.model_admin
```

打开 `http://127.0.0.1:8765`，保存后会更新根目录 `model-routing.yaml`。

## MCP 调用

MCP 服务器配置在根目录 `tool-concurrency.yaml` 的 `mcp_servers` 节。启动
agent 时，代码会按 `tool_groups` / `agent_tools` 加载本 agent 可见的工具。

iFind 使用一套共享 key，放在 workspace 根目录 `.env`：

```bash
IFIND_MCP_TOKEN=...
# 或完整 raw Authorization header
IFIND_MCP_AUTHORIZATION=...
```

东方财富妙想 MX DS MCP 配置为 `mx-ds-mcp`，同样只从 `.env` 读取凭证：

```bash
MX_DS_MCP_API_KEY=...
```

`tool-concurrency.yaml` 只保存 MCP URL、transport、非敏感 header 占位、
tool group allowlist、搜索默认值和输出目录，不保存真实 token/header。

## 输出目录

产物默认写入最外层 workspace 的 `out/<YYYYMMDD-HHMMSS>/`。同一次任务的
markdown、Excel、PPT 应放在同一个时间戳目录里。测试或复现时可以固定时间戳：

```bash
MARKET_RESEARCHER_OUTPUT_TIMESTAMP=20260531-120000
```

## 运行测试

```bash
python -m pytest
```

测试覆盖了配置解析、env 覆盖，以及时间戳输出目录逻辑。
