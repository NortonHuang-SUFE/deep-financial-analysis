# DCF Builder

LangGraph DCF valuation agent. The graph entry is `dcf_builder` in
`langgraph.json`.

## Model Gateway

Model profiles and agent/subagent bindings live in the workspace root
`../model-routing.yaml`. Keep only live credentials in the workspace root
`../.env`:

```bash
DASHSCOPE_API_KEY=
MINIMAX_API_KEY=
ARK_API_KEY=
```

Edit model routing with the local admin page:

```bash
.venv/bin/python -m financial_agent_runtime.model_admin
```

Open `http://127.0.0.1:8765`; saving writes `model-routing.yaml`.

## MCP Keys

iFind uses the same key across all configured iFind MCP servers. Put it once in
the workspace root `../.env`:

```bash
IFIND_MCP_TOKEN=
```

That is sent as `Authorization: Bearer <token>` to every `ifind-*` server.

If iFind gives you the full raw Authorization header value instead, use:

```bash
IFIND_MCP_AUTHORIZATION=
```

MCP URLs, search defaults, output defaults, and tool grants live in the
workspace root `tool-concurrency.yaml`; live credentials stay only in `.env`.

Eastmoney MX DS MCP is configured as `mx-ds-mcp` anywhere this project already
uses iFind MCP. Put its credential in the same workspace `.env`:

```bash
MX_DS_MCP_API_KEY=
```

The workspace root `tool-concurrency.yaml` keeps parent and
`dcf-assumption-researcher` tool grants, including their MCP allowlists.

## Test

```bash
python -m pytest
```
