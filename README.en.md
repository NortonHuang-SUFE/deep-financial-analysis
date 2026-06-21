# China Market Investment Research Agent System

[中文主页](README.md)

A multi-agent research workflow for China public markets. It connects pre-market notes, sector research, thematic scans, investment theses, single-stock coverage, three-statement models, DCF valuation, and chart packs into a local, auditable production system.

![System topology](docs/assets/system-topology.png)

> Disclaimer: this project produces research workpapers and analytical materials. It does not provide investment advice. Outputs should be reviewed by qualified professionals before use.

## 1. What Anthropic's Financial Skills / Agents Are

On May 5, 2026, Anthropic released ten ready-to-run financial-services agent templates for investment banking, asset management, finance, and compliance workflows. See [Agents for financial services](https://www.anthropic.com/news/finance-agents) and [anthropics/financial-services](https://github.com/anthropics/financial-services).

| Agent | Typical use |
|---|---|
| `pitch-builder` / `meeting-preparer` | Pitch materials, client meetings, banker workflows |
| `earnings-reviewer` / `market-researcher` | Earnings review, market and company research |
| `model-builder` / `valuation-reviewer` | Financial model building and valuation review |
| `gl-reconciler` / `month-end-closer` / `statement-auditor` | Close, reconciliation, and financial statement review |
| `kyc-screener` | KYC, compliance, and client screening |

Anthropic's system is best understood as an enterprise financial-workflow template marketplace. It depends on Claude surfaces, connectors, and institutional data permissions.

## 2. Why This Project Is Different

| Dimension | Anthropic Financial Agents | This project |
|---|---|---|
| Platform | Claude Cowork, Claude Code plugin, or Managed Agents | Python, LangGraph, local files, and an OpenAI-compatible model gateway |
| Market | Broad global financial workflows | Native A-share, HK, Chinese ADR, China macro, announcements, northbound/southbound, ETF, Dragon-Tiger List, futures, and earnings-season context |
| Data | Overseas financial connectors and enterprise data | Tonghuashun iFind MCP for stocks, funds, macro, news, bonds, global equities, and indices |
| Logic | Skills and workflow templates | Equity research chain: morning note -> sector/theme -> screen -> thesis -> coverage -> model -> valuation -> charts/report |
| Outputs | Enterprise review and Office workflows | Markdown, JSON, Excel, PPT, PNG charts, and synthesis reports |
| Auditability | Platform logs | Local artifacts: source logs, run manifests, model audits, valuation states |

In short: Anthropic is strong at general enterprise financial templates; this project is built for local China equity research production.

## 3. Public Examples

Only three representative examples are kept in `docs/examples/`, so they remain readable on GitHub:

| Example | Link | Capability |
|---|---|---|
| Morning note | [A-share Morning Note](docs/examples/a-share-morning-note.md) | Overnight markets, policy, announcements, capital flows, and trading themes |
| Sector research | [MLCC sector research](docs/examples/mlcc-sector-research.md) | Supply-demand, value chain, competitive landscape, key stocks, and risks |
| Company research | [Shaanxi Coal company research](docs/examples/shaanxi-coal-company-research.md) | Business model, cost structure, governance, moat, and risks |

## 4. Configuration

Requirements:

- Python 3.11
- OpenAI-compatible model gateway, defaulting to `https://dashscope.aliyuncs.com/compatible-mode`
- Tonghuashun iFind MCP token or raw Authorization header

Install:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ./DCF-builder -e ./industry-ananlysis -e ./morning-note \
  -e ./screen -e ./sector -e ./thesis -e ./orchestrator \
  -e ./single-stock-coverage
```

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

Common graphs: `deep_orchestrator`, `morning_note`, `market_researcher`, `sector_research`, `stock_screen`, `thesis_tracker`, `single_stock_coverage`, `dcf_builder`.

## 5. Version, Roadmap, and Contact

Current version: `v0.1 research-preview`, as of 2026-06-21.

Implemented:

- Top-level orchestrator and core research agents
- Unified Tonghuashun iFind MCP data access
- Morning notes, sector research, capital-flow scans, announcement scans, thesis tracking, single-stock coverage, three-statement models, DCF, and chart packs
- Local Markdown / JSON / Excel / PPT / PNG artifacts

Next:

- Polish final single-stock coverage reports
- Stabilize stock screens and watchlist explanations
- Standardize source logs, citations, and public samples
- Add portfolio tracking, backtesting, and automatic thesis scorecard updates

Contact:

- Email: huang.shengsong1@gmail.com
- Issues and feature requests: open an issue in this project
