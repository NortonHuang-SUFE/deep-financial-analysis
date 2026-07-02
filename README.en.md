# Deep Financial Analysis

[中文主页](README.md)

A multi-agent research system for China public markets. It connects pre-market intelligence, sector research, stock screening, single-stock research, three-statement modeling, DCF valuation, and chart packs into a local, auditable workflow.

> Disclaimer: this project produces research workpapers and analytical materials. It does not provide investment advice. Outputs should be reviewed by qualified professionals before use.

<p align="center">
  <img src="docs/assets/agentic-architecture-overview.png" alt="Deep Financial Analysis agentic architecture overview" width="900"><br>
  <em>System architecture: the orchestrator fans out to 7 top-level specialist agents and 13 internal single-stock coverage agents.</em>
</p>

## 1. What This Project Is

`Deep Financial Analysis` is designed as a local equity-research workflow system for China public markets. It decomposes research work into specialized agents and lets them collaborate around one research task.

It currently covers:

- Morning notes: overnight markets, policy, announcements, capital flows, and trading ideas
- Sector research: value chain, competitive landscape, key stocks, and risk variables
- Stock screening: A-share / HK thematic screens, factor screens, and watchlists
- Single-stock research: company profile, business model, cost structure, governance, moat, and risks
- Financial modeling and valuation: three-statement model, model audit, DCF, comps, and valuation reconciliation
- Charts and reports: chart packs, PPT/Markdown research materials, and final synthesis reports

The data layer is built around Tonghuashun iFind MCP. Model calls go through an OpenAI-compatible gateway, with DashScope/Qwen as the default and replaceable backend.

## 2. What It Produces

| Output | Description |
|---|---|
| `morning-note.md` | A-share pre-market briefing covering global markets, commodities, FX, policy, company events, and flows |
| Sector / thematic reports | Supply-demand, value chain, competitive landscape, A-share targets, catalysts, and risks |
| Stock screens | Candidate stocks and watchlists driven by themes, factors, flows, or events |
| Single-stock research | Company identity, business breakdown, profit drivers, governance, moat, and risks |
| `integrated_model.xlsx` | Linked three-statement model, revenue build, working capital, PP&E, debt, and DCF inputs |
| Valuation analysis | DCF, trading comps, historical multiples, market-implied checks, valuation reconciliation, and scenarios |
| Chart packs | Football field, sensitivity analysis, scenario comparison, risk matrix, catalyst timeline, and more |

## 3. Public Examples

The following three examples represent the system's current core capabilities and are directly readable on GitHub:

| Example | Link | Capability |
|---|---|---|
| Morning note | [A-share Morning Note](docs/examples/a-share-morning-note.md) | Overnight markets, policy, announcements, capital flows, and trading themes |
| Sector research | [MLCC sector research](docs/examples/mlcc-sector-research.md) | Supply-demand, value chain, competitive landscape, key stocks, and risks |
| Single-stock research | [Shaanxi Coal company research](docs/examples/shaanxi-coal-company-research.md) | Business model, cost structure, governance, moat, and risks |

### Sample head images (HTML image rendering)

Both images below are real run artifacts produced by `html_image_renderer` from HTML Anything style templates (single-page PNGs for desktop):

<p align="center">
  <img src="docs/assets/sample-leverage-flows-dashboard.png" alt="Pre-market margin-flow head image" width="640"><br>
  <em>Pre-market margin-flow head image: divergent leverage signals across two names (2026-06-26)</em>
</p>

<p align="center">
  <img src="docs/assets/sample-storage-chain-poster.png" alt="Market-theme editorial poster" width="300"><br>
  <em>Market-theme editorial poster: storage-chain breakout / margin balance tops RMB 30tn (2026-06-24)</em>
</p>

## 4. Design Positioning: Compared With Anthropic Financial Agents

On May 5, 2026, Anthropic released ten ready-to-run financial-services agent templates for investment banking, asset management, finance, and compliance workflows. See [Agents for financial services](https://www.anthropic.com/news/finance-agents) and [anthropics/financial-services](https://github.com/anthropics/financial-services).

Anthropic's agents are positioned closer to an enterprise financial-workflow template marketplace: pitch builder, meeting preparer, earnings reviewer, market researcher, model builder, valuation reviewer, statement auditor, KYC screener, and related workflows.

`Deep Financial Analysis` starts from a different premise. It is organized around China public-market research rather than a general collection of financial skills.

| Dimension | Anthropic Financial Agents | Deep Financial Analysis |
|---|---|---|
| Positioning | General financial-services agent templates | China public-market research production system |
| Platform | Claude Cowork, Claude Code plugin, or Managed Agents | Python, LangGraph, local files, and replaceable model gateway |
| Market | Broad global financial workflows | Native A-share, HK, Chinese ADR, China macro, announcements, northbound/southbound, ETF, Dragon-Tiger List, futures, and earnings-season context |
| Data | Overseas financial connectors and enterprise data | Tonghuashun iFind MCP for stocks, funds, macro, news, bonds, global equities, and indices |
| Logic | Skills and workflow templates | Morning note -> sector/theme -> screen -> single-stock research -> model -> valuation -> charts/report |
| Outputs | Enterprise review and Office workflows | Markdown, JSON, Excel, PPT, PNG charts, and synthesis reports |
| Auditability | Platform logs | Local artifacts: source logs, run manifests, model audits, valuation states |

In short: Anthropic is strong at general enterprise financial templates; this project is built for complete local China equity research workflows.

## 5. Configuration

Requirements:

- Python 3.11
- OpenAI-compatible model gateway, defaulting to `https://dashscope.aliyuncs.com/compatible-mode`
- Tonghuashun iFind MCP token or raw Authorization header

Install:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ./financial-agent-runtime \
  -e ./DCF-builder -e ./industry-ananlysis -e ./morning-note \
  -e ./screen -e ./sector -e ./thesis -e ./orchestrator \
  -e ./html-image-renderer -e ./single-stock-coverage
```

> `financial-agent-runtime` is the shared runtime package used by every agent
> and must be installed first; otherwise startup fails with
> `ModuleNotFoundError: No module named 'financial_agent_runtime'`.

Configure:

```bash
cp .env.example .env
```

Minimum `.env` values:

```bash
# model-routing.yaml stores only api_key_env names; live model keys stay in .env.
DASHSCOPE_API_KEY=...
MINIMAX_API_KEY=...
ARK_API_KEY=...

# choose one
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=Bearer ...

# optional for projects that already use iFind MCP: Eastmoney MX DS MCP
MX_DS_MCP_API_KEY=...
```

Edit model profiles, `api_key_env` names, and agent/subagent bindings with the
local admin page:

```bash
.venv/bin/python -m financial_agent_runtime.model_admin
```

Then open `http://127.0.0.1:8765`; saving writes the workspace
`model-routing.yaml`.
`model-routing.yaml` is tracked and stores only model profiles, agent bindings,
and `api_key_env` variable names, never live keys.
In `model-routing.yaml`, `default_model` sets the primary default model and
`default_multimodal_model` sets the default multimodal fallback. Individual
agents/subagents can override both with `agent_models.<name>.model` and
`agent_models.<name>.multimodal_fallback_model`.

iFind MCP URLs are stored in the root `tool-concurrency.yaml` under `mcp_servers`:

| Server | URL |
|---|---|
| `ifind-stock` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-stock-mcp` |
| `ifind-fund` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-fund-mcp` |
| `ifind-edb` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-edb-mcp` |
| `ifind-news` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-news-mcp` |
| `ifind-bond` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-bond-mcp` |
| `ifind-global-stock` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-global-stock-mcp` |
| `ifind-index` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-index-mcp` |

Eastmoney MX DS MCP is also configured in the root `tool-concurrency.yaml`:

| Server | URL |
|---|---|
| `mx-ds-mcp` | `https://mxapi.eastmoney.com/mxds/mcp` |

`mx-ds-mcp` reads `MX_DS_MCP_API_KEY` from `.env` and sends it as the `em_api_key` header. The workspace root `tool-concurrency.yaml` also owns `agent_configs`, `tool_groups`, and `agent_tools`, including each agent/subagent's MCP access, local tools, search defaults, and output directory.

External-tool concurrency limits also live in `tool-concurrency.yaml` at the workspace root. This file also stores required agent/subagent tool grants, so keep it present. Its `groups` section contains shared budgets: when in-flight calls in a group reach `max_concurrency`, further calls queue and run serially. By default every `ifind-*` server shares one `ifind` group (limit 5), while `mx-ds-mcp` has its own `mx-ds` group (limit 2), so the orchestrator fanning out to many subagents will not overwhelm external services. Edit the threshold, add groups, or pull named tools (e.g. `web_search`) into a budget via `tools:` globs; the limit is shared process-wide. A missing or empty `groups` section only disables concurrency limiting; tool grants are still required.

Run:

```bash
.venv/bin/langgraph dev
```

After startup, choose either the top-level orchestrator or an individual research agent in LangGraph. For composite tasks, start with `deep_orchestrator`.

### Run modes: local / cloud sandbox

Since v0.2 the system supports two file backends, switchable via the `AGENT_BACKEND` environment variable (default `local`):

| Mode | `AGENT_BACKEND` | Description |
|---|---|---|
| Local | `local` (default) | Code execution and artifact I/O happen on the host filesystem (`LocalShellBackend` / `FilesystemBackend`); outputs land under `AGENT_FILE_STORAGE_ROOT` (the repo workspace when empty). Best for fast development, debugging, and single-machine review. |
| Cloud (experimental) | `daytona` | Each process spins up an ephemeral [Daytona](https://www.daytona.io/) cloud sandbox; the agents' code execution and artifact writes happen inside the sandbox, with the artifact root set by `DAYTONA_FILE_STORAGE_ROOT` (a Linux path inside the sandbox). Best for isolated execution, a uniform Linux runtime, and keeping the host clean. |

Cloud mode needs Daytona credentials in `.env`:

```bash
AGENT_BACKEND=daytona
DAYTONA_API_KEY=...
DAYTONA_API_URL=https://app.daytona.io/api
DAYTONA_FILE_STORAGE_ROOT=/home/daytona/financial-analysis
```

Both modes share the same agent code and skills; switching the backend requires no changes to business logic.

## 6. Version, Roadmap, and Contact

Current version: `v0.4.1 research-preview`, as of 2026-07-02.

The full version history lives in [CHANGELOG.en.md](CHANGELOG.en.md) (中文版: [CHANGELOG.md](CHANGELOG.md)).

Implemented:

- Top-level orchestrator and core research agents
- Local and cloud (Daytona sandbox) run backends, switchable via `AGENT_BACKEND`
- Root-level `model-routing.yaml` model routing, a local model configuration UI, and multimodal fallback model settings
- Root-level `tool-concurrency.yaml` tool grants, MCP configuration, and external-tool concurrency limits
- Unified Tonghuashun iFind MCP data access
- Morning notes, sector research, capital-flow scans, announcement scans, single-stock research, three-statement models, DCF, and chart packs
- Local Markdown / JSON / Excel / PPT / PNG artifacts

Next:

- Improve final single-stock research reports
- Stabilize stock screens and watchlist explanations
- Standardize source logs, citations, and public samples
- Add portfolio tracking, backtesting, and automatic investment-logic scorecard updates

Contact:

- Email: huang.shengsong1@gmail.com
- Issues and feature requests: open an issue in this project
