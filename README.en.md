# Daily Report Agent

[中文](README.md)

A focused China-market daily report agent for generating A-share pre-market notes and optional report cover images or visual summaries. The project is composed of one public LangGraph graph and two internal capabilities:

- `morning_note`: generates an A-share pre-market Morning Note / daily report as Markdown plus JSON source artifacts.
- `html_image_renderer`: reads report artifacts and renders one HTML-based PNG cover or visual summary.

The only public LangGraph graph is `daily_report`. The project is intentionally scoped out of valuation modeling, single-stock coverage, sector deep dives, stock screening, and thesis tracking.

> Disclaimer: outputs are research notes and information drafts, not investment advice. Qualified professionals should review all conclusions.

## Outputs

| Output | Description |
|---|---|
| `morning-note.md` | A-share pre-market daily report covering overnight markets, policy, company events, flows, and the day's calendar |
| `morning-note-sources.json` | Structured source and validation artifact |
| `png/<seq>.png` | Optional report cover / visual summary rendered by `html_image_renderer` |
| `daily-report-summary.md` | Coordinator summary and artifact index |

## Setup

Requirements:

- Python 3.11
- OpenAI-compatible model gateway
- Tonghuashun iFind MCP token or raw Authorization header
- Optional Eastmoney MX DS MCP key

Install:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ./financial-agent-runtime \
  -e ./morning-note -e ./orchestrator -e ./html-image-renderer
```

Configure:

```bash
cp .env.example .env
```

Fill at least:

```bash
DASHSCOPE_API_KEY=...
ARK_API_KEY=...

IFIND_MCP_TOKEN=...
# or
IFIND_MCP_AUTHORIZATION=Bearer ...
```

You can edit model profiles and agent bindings with:

```bash
.venv/bin/python -m financial_agent_runtime.model_admin
```

Open `http://127.0.0.1:8765`. Live secrets stay in `.env`.

## Run

Development server:

```bash
.venv/bin/langgraph dev --no-browser --no-reload
```

Choose `daily_report`. Example request:

```text
生成今天 A 股开盘前日报，并额外做一张 16:9 头图。
```

## Local / Intranet Docker

`langgraph.json` is the official LangGraph deployment interface. `graphs` controls public assistants and `dependencies` controls packages installed into the container. This project exposes only `daily_report`.

Generate a Dockerfile:

```bash
.venv/bin/langgraph dockerfile -c langgraph.json /private/tmp/daily-report.Dockerfile
```

Validate with a production-like local stack:

```bash
.venv/bin/langgraph up --recreate --wait --port 8123
curl http://127.0.0.1:8123/ok
```

The Docker image installs Chromium and CJK fonts and sets `HTML_IMAGE_RENDERER_BROWSER=/usr/bin/chromium` for PNG rendering.

## Tests

```bash
.venv/bin/python -m pytest financial-agent-runtime/tests morning-note/tests html-image-renderer/tests orchestrator/tests
```

## Version

Current version: `v0.1.4`.

See [CHANGELOG.md](CHANGELOG.md) and [CHANGELOG.en.md](CHANGELOG.en.md).
