# Morning Note

Morning Note 是一个独立的 LangGraph Deep Agents 项目，用于生成中国市场 A 股开盘前早会纪要。它优先使用 iFind MCP 与妙想 MX DS MCP，覆盖隔夜美股/港股/中概、商品、汇率、政策监管、交易所公告、上市公司公告、业绩快报/预告、机构调研、龙虎榜、北向资金、ETF 和期指等信息。

## 配置

项目目录：`morning-note/`

Python 包名：`morning_note_agent`

LangGraph graph 名：`morning_note`

`config.yaml` 只包含安全默认值和 iFind MCP URL。密钥请放在 workspace 根目录 `.env`，也就是 `morning-note/../.env`，不要放在项目内 `.env`。

常用环境变量：

```bash
MODEL_NAME=qwen-3.7-max
MODEL_GATEWAY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
MODEL_GATEWAY_API_KEY=...

IFIND_MCP_TOKEN=...
# 或
IFIND_MCP_AUTHORIZATION="Bearer ..."
MX_DS_MCP_API_KEY=...
```

支持按 server 覆盖 URL/transport，但 iFind 鉴权仍只使用上面的共享 key：

```bash
IFIND_NEWS_MCP_URL=https://...
IFIND_NEWS_MCP_TRANSPORT=streamable_http
MX_DS_MCP_URL=https://mxapi.eastmoney.com/mxds/mcp
MX_DS_MCP_TRANSPORT=streamable-http
```

已配置的 iFind MCP：

- `ifind-stock`
- `ifind-fund`
- `ifind-edb`
- `ifind-news`
- `ifind-bond`
- `ifind-global-stock`
- `ifind-index`
- `mx-ds-mcp`

可用 `config.yaml` 的 `mcp_tool_groups.default.servers` 收窄本 agent 可用的
MCP server。

测试或离线调试时可设置：

```bash
MORNING_NOTE_TEST_MODE=1
MORNING_NOTE_DISABLE_MCP=1
```

## 运行

从项目目录运行：

```bash
cd morning-note
../.venv/bin/langgraph dev
```

或用 LangGraph 配置文件加载：

```bash
cd morning-note
../.venv/bin/python -m langgraph dev
```

`langgraph.json` 指向：

```text
./src/morning_note_agent/graph.py:graph
```

并读取：

```text
../.env
```

## 输出

本地工具默认写入 `config.yaml` 的 `output.dir`，相对路径会从共享文件根目录解析；如果 `.env` 设置了 `AGENT_FILE_STORAGE_ROOT`，则以它为根目录：

```text
${AGENT_FILE_STORAGE_ROOT:-workspace}/out/<YYYYMMDD-HHMMSS>/
```

同一次 LangGraph run/thread 会复用同一个时间戳目录；没有 run/thread 标识时，进程级缓存只短时间复用，避免长跑服务串到旧任务。需要固定输出目录时设置：

```bash
MORNING_NOTE_OUTPUT_TIMESTAMP=20260602-083000
```

可用工具：

- `create_task_output_dir`
- `write_markdown_report`
- `write_json_artifact`

最终 Markdown Morning Note 会保存到对应时间戳目录；来源日志、公司事件、今日日程等结构化数据可以保存为 JSON artifact。工具返回绝对路径，方便 orchestrator 和 Studio 日志直接定位真实文件。

## 测试

从 workspace 根目录运行：

```bash
.venv/bin/python -m pytest morning-note/tests
```
