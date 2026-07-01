# Market Researcher

LangGraph Deep Agents 行业研究项目，入口是 `langgraph.json` 中的
`market_researcher` graph。

## 配置从哪里来

项目默认从本目录读取非敏感配置，并从 workspace 根目录读取密钥：

- `config.yaml`：模型、MCP、搜索、输出目录的默认配置。
- `../.env`：本机密钥和临时覆盖项，优先级高于 `config.yaml`。
- 进程环境变量：如果启动命令里已经设置，同样优先级高于 `config.yaml`。

代码会锚定到项目根目录解析 `config.yaml`，并统一读取父级 workspace 的
`.env`。不要把真实 key 放进 `config.yaml`。

## 大模型调用

模型配置在 `config.yaml` 的 `model` 节，也可以用 `.env` 覆盖：

```bash
MODEL_GATEWAY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
MODEL_NAME=qwen-3.7-max
MODEL_GATEWAY_API_KEY=...
MODEL_MAX_TOKENS=16000
MODEL_THINKING=auto
```

如果 `MODEL_GATEWAY_API_KEY` 为空，代码会按 `MODEL_GATEWAY_BASE_URL` 自动查找
`DASHSCOPE_API_KEY` 或 `ALIBABA_API_KEY`。

## MCP 调用

MCP 服务器配置在 `config.yaml` 的 `mcp` 节。启动 agent 时，
`src/market_researcher/graph.py` 会读取所有非空 URL 的服务器，并通过
`langchain-mcp-adapters` 加载工具。

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

`config.yaml` 只保留 MCP URL、transport、非敏感 header 占位和 tool group
allowlist，不保存真实 token/header。

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
