# Morning Note

Morning Note 是一个独立的 LangGraph Deep Agents 项目，用于生成中国市场 A 股开盘前早会纪要。它优先使用 iFind MCP，覆盖隔夜美股/港股/中概、商品、汇率、政策监管、交易所公告、上市公司公告、业绩快报/预告、机构调研、龙虎榜、北向资金、ETF 和期指等信息。

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
```

支持按 server 覆盖 URL/transport，但 iFind 鉴权仍只使用上面的共享 key：

```bash
IFIND_NEWS_MCP_URL=https://...
IFIND_NEWS_MCP_TRANSPORT=streamable_http
```

已配置的 iFind MCP：

- `ifind-stock`
- `ifind-fund`
- `ifind-edb`
- `ifind-news`
- `ifind-bond`
- `ifind-global-stock`
- `ifind-index`

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

本地工具会写入 workspace 根目录：

```text
out/<YYYYMMDD-HHMMSS>/
```

同一次任务复用同一个时间戳目录。需要固定输出目录时设置：

```bash
MORNING_NOTE_OUTPUT_TIMESTAMP=20260602-083000
```

可用工具：

- `create_task_output_dir`
- `write_markdown_report`
- `write_json_artifact`

最终 Markdown Morning Note 会保存到对应时间戳目录；来源日志、公司事件、今日日程等结构化数据可以保存为 JSON artifact。

## 测试

从 workspace 根目录运行：

```bash
.venv/bin/python -m pytest morning-note/tests
```
