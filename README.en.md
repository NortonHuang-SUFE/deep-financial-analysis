# Deep Financial Analysis

[中文主页](README.md)

A multi-agent research system for China public markets. It connects pre-market intelligence, sector research, stock screening, single-stock research, three-statement modeling, DCF valuation, and chart packs into a local, auditable workflow.

> Disclaimer: this project produces research workpapers and analytical materials. It does not provide investment advice. Outputs should be reviewed by qualified professionals before use.

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
MODEL_GATEWAY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
MODEL_GATEWAY_API_KEY=...
MODEL_NAME=qwen-3.7-max
MODEL_MAX_TOKENS=16000

# choose one
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=Bearer ...
```

iFind MCP URLs are already stored in each subproject's `config.yaml`:

| Server | URL |
|---|---|
| `ifind-stock` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-stock-mcp` |
| `ifind-fund` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-fund-mcp` |
| `ifind-edb` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-edb-mcp` |
| `ifind-news` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-news-mcp` |
| `ifind-bond` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-bond-mcp` |
| `ifind-global-stock` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-global-stock-mcp` |
| `ifind-index` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-index-mcp` |

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

Current version: `v0.2 research-preview`, as of 2026-06-28.

### Change Log

#### v0.2.0 - 2026-06-28

- Added a cloud run mode: with `AGENT_BACKEND=daytona`, all agents execute and persist artifacts inside an ephemeral Daytona cloud sandbox; the default stays `local`, and both modes share one agent codebase.
- Extracted a shared `financial-agent-runtime` package that centralizes backend selection, artifact storage root, skills mirroring, artifact writes, and general-purpose subagent disabling, removing the duplicated per-agent implementations.
- `.env.example` documents `AGENT_BACKEND`, `DAYTONA_*` credentials, and `DAYTONA_FILE_STORAGE_ROOT` (bilingual comments).
- Install instructions now include the shared `financial-agent-runtime` package; `langgraph.json` registers it as the first dependency.
- Added regression tests for the cloud/local backends and artifact paths.

#### v0.1.1 - 2026-06-25

- Unified the artifact directory contract between the orchestrator and subagents: each composite run now uses one mother folder, with all subagent outputs nested recursively underneath it.
- Made upstream `output_dir` values exact task directories for `morning_note`, `stock_screen`, `sector_research`, `thesis_tracker`, and `market_researcher`, avoiding accidental second-level timestamp folders.
- Updated `html_image_renderer` orchestration rules so it writes `html/` and `png/` directly under the assigned renderer subdirectory.
- Synchronized mounted skill documentation so skills no longer instruct agents to create a separate top-level `out/<timestamp>` directory during orchestrated runs.
- Added regression coverage for artifact root / output directory behavior.

#### v0.1.0 - 2026-06-21

- Initial research-preview with core research agents, Tonghuashun iFind MCP access, local artifact output, three-statement modeling, DCF, chart packs, and HTML image rendering.

Implemented:

- Top-level orchestrator and core research agents
- Local and cloud (Daytona sandbox) run backends, switchable via `AGENT_BACKEND`
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
