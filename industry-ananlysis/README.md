# Market Researcher

LangGraph Deep Agents 行业研究项目，入口是 `langgraph.json` 中的
`market_researcher` graph。

## 配置从哪里来

项目默认从本目录读取配置：

- `config.yaml`：模型、MCP、搜索、输出目录的默认配置。
- `.env`：本机密钥和临时覆盖项，优先级高于 `config.yaml`。
- 进程环境变量：如果启动命令里已经设置，同样优先级高于 `config.yaml`。

代码现在会锚定到项目根目录解析 `config.yaml` 和 `.env`，所以从
`industry-ananlysis/` 内启动，或从父级 workspace 启动，读取的是同一套配置。

## 大模型调用

模型配置在 `config.yaml` 的 `model` 节，也可以用 `.env` 覆盖：

```bash
MODEL_BASE_URL=https://api.minimaxi.com
MODEL_NAME=MiniMax-M2.7
MODEL_API_KEY=...
MODEL_MAX_TOKENS=16000
MODEL_THINKING=auto
```

如果 `MODEL_API_KEY` 为空，代码会按 `MODEL_BASE_URL` 自动查找对应的 provider
key，例如 `MINIMAX_API_KEY`、`DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`。

## MCP 调用

MCP 服务器配置在 `config.yaml` 的 `mcp` 节。启动 agent 时，
`src/market_researcher/graph.py` 会读取所有非空 URL 的服务器，并通过
`langchain-mcp-adapters` 加载工具。

iFind 这类 raw Authorization header 可以放在 `.env`：

```bash
IFIND_STOCK_MCP_AUTHORIZATION=...
IFIND_FUND_MCP_AUTHORIZATION=...
IFIND_NEWS_MCP_AUTHORIZATION=...
```

环境变量里的 server 名称把 `config.yaml` 的横杠换成下划线，例如
`ifind-stock` 对应 `IFIND_STOCK_*`。

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
