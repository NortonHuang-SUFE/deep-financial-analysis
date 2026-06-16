# Deep Financial Analysis

Multi-agent LangGraph workspace for financial research, screening, valuation,
morning notes, thesis tracking, and single-stock coverage.

## Configuration

1. Use Python 3.11.
2. Create `.env` from `.env.example` and fill the required keys:

```bash
cp .env.example .env
```

Required model settings:

```bash
MODEL_GATEWAY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
MODEL_GATEWAY_API_KEY=...
MODEL_NAME=qwen-3.7-max
MODEL_MAX_TOKENS=16000
```

Optional data/tool settings:

```bash
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=...
AGENT_FILE_STORAGE_ROOT=/absolute/path/for/artifacts
```

Leave `AGENT_FILE_STORAGE_ROOT` empty to write generated files under this repo.

## Install

Install the agent packages you plan to run:

```bash
pip install -e ./DCF-builder -e ./industry-ananlysis -e ./morning-note \
  -e ./screen -e ./sector -e ./thesis -e ./orchestrator \
  -e ./single-stock-coverage
```

## Run

The workspace graph registry is `langgraph.json`. Main graph names:

- `deep_orchestrator`
- `single_stock_coverage`
- `dcf_builder`
- `market_researcher`
- `morning_note`
- `stock_screen`
- `sector_research`
- `thesis_tracker`

Each subproject also has its own `config.yaml` for model, MCP, and output
defaults.
