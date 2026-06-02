# DCF Builder

LangGraph DCF valuation agent. The graph entry is `dcf_builder` in
`langgraph.json`.

## Model Gateway

All model calls use one OpenAI-compatible gateway / relay. Configure the relay
once in `.env`:

```bash
MODEL_GATEWAY_BASE_URL=https://api.babelark.com
MODEL_GATEWAY_API_KEY=...
```

Choose which model to use with `MODEL_PROFILE`. It can be a configured preset:

```bash
MODEL_PROFILE=minimax
```

Or a direct model ID that is not listed in `config.yaml`:

```bash
MODEL_PROFILE=qwen3.6-max-preview
```

Profiles live in `config.yaml` under `model.profiles` only for shared defaults
such as `max_tokens` and `thinking`. Add or edit profiles there when you want a
named preset; direct model IDs do not need registration or code changes:

```yaml
model:
  active: "minimax"
  profiles:
    minimax:
      name: "MiniMax-M2.7"
      max_tokens: 16000
      thinking: "auto"
    qwen:
      name: "qwen3-max"
      max_tokens: 32000
      thinking: "auto"
    qwen3.6-max-preview:
      name: "qwen3.6-max-preview"
      max_tokens: 32000
      thinking: "auto"
```

`MODEL_NAME`, `MODEL_MAX_TOKENS`, and `MODEL_THINKING` still work as direct
overrides when you need a one-off run.

## iFind MCP Key

iFind uses the same key across all configured iFind MCP servers. Put it once in
`.env`:

```bash
IFIND_MCP_TOKEN=...
```

That is sent as `Authorization: Bearer <token>` to every `ifind-*` server.

If iFind gives you the full raw Authorization header value instead, use:

```bash
IFIND_MCP_AUTHORIZATION=...
```

Per-server overrides like `IFIND_STOCK_MCP_TOKEN` still work, but they are no
longer the recommended path.

## Test

```bash
python -m pytest
```
