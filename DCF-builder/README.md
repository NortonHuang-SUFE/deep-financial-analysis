# DCF Builder

LangGraph DCF valuation agent. The graph entry is `dcf_builder` in
`langgraph.json`.

## Model Gateway

All model calls default to Alibaba DashScope's OpenAI-compatible gateway.
Configure live values once in the workspace root `../.env`:

```bash
MODEL_GATEWAY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
MODEL_GATEWAY_API_KEY=
# or DASHSCOPE_API_KEY=
```

Choose which model to use with `MODEL_PROFILE`. It can be a configured preset:

```bash
MODEL_PROFILE=qwen
```

Or a direct model ID that is not listed in `config.yaml`:

```bash
MODEL_PROFILE=qwen-3.7-max
```

Profiles live in `config.yaml` under `model.profiles` only for shared defaults
such as `max_tokens` and `thinking`. Add or edit profiles there when you want a
named preset; direct model IDs do not need registration or code changes:

```yaml
model:
  active: "qwen"
  profiles:
    qwen:
      name: "qwen-3.7-max"
      max_tokens: 16000
      thinking: "auto"
```

`MODEL_NAME`, `MODEL_MAX_TOKENS`, and `MODEL_THINKING` still work as direct
overrides when you need a one-off run.

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

Do not put iFind keys in `config.yaml`; it contains only safe MCP URLs and
non-secret defaults.

Eastmoney MX DS MCP is configured as `mx-ds-mcp` anywhere this project already
uses iFind MCP. Put its credential in the same workspace `.env`:

```bash
MX_DS_MCP_API_KEY=
```

`config.yaml` keeps parent and assumption-researcher MCP allowlists under
`mcp_tool_groups`.

## Test

```bash
python -m pytest
```
