# Sector Research Agent

`sector/` 是一个独立的 LangGraph Deep Agents 中国行业研究项目，graph 名为 `sector_research`，Python 包名为 `sector_research_agent`。

## 配置

配置文件位于 `sector/config.yaml`，只包含模型默认值和 iFind MCP URL，不包含任何 token。

默认模型：

- `MODEL_NAME`: `qwen-3.7-max`
- `MODEL_GATEWAY_BASE_URL`: `https://dashscope.aliyuncs.com/compatible-mode`

认证从 workspace 根目录 `.env` 读取，也就是 `financialServicesModified/.env`，不是 `sector/.env`。常用环境变量：

```bash
MODEL_GATEWAY_API_KEY=...
DASHSCOPE_API_KEY=...
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=...
```

iFind 鉴权只支持共享 key；单 server 只允许覆盖 URL/transport，例如：

```bash
IFIND_EDB_MCP_URL=https://example.test/mcp
IFIND_EDB_MCP_TRANSPORT=streamable_http
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
