# 中国市场投研 Agent 系统

[English](README.en.md)

面向中国二级市场的多 Agent 投研工作流。它把盘前信息、行业研究、主题扫描、个股 thesis、单股覆盖、三表模型、DCF 估值和图表包串成一条本地可复盘的生产线。

![系统拓扑图](docs/assets/system-topology.png)

> 免责声明：本项目生成的是投研工作底稿和分析材料，不构成投资建议。所有结论都应由具备资质的专业人士复核。

## 1. A 社的 Financial Skills / Agents 是什么

Anthropic（A 社）在 2026-05-05 发布了面向金融服务的 10 个 ready-to-run agent templates，覆盖投行、资管、财务和合规场景。官方资料见 [Agents for financial services](https://www.anthropic.com/news/finance-agents) 和 [anthropics/financial-services](https://github.com/anthropics/financial-services)。

这些 agents 主要包括：

| Agent | 典型用途 |
|---|---|
| `pitch-builder` / `meeting-preparer` | 投行 pitch、会议准备和客户材料 |
| `earnings-reviewer` / `market-researcher` | 财报解读、市场和公司研究 |
| `model-builder` / `valuation-reviewer` | 财务模型构建与估值复核 |
| `gl-reconciler` / `month-end-closer` / `statement-auditor` | 财务关账、对账和报表审计 |
| `kyc-screener` | KYC、合规和客户筛查 |

它的定位更像“企业金融工作流模板市场”：依赖 Claude 平台、企业连接器和已有数据权限，适合嵌入投行、审计、财务和合规流程。

## 2. 这个项目好在哪里

| 维度 | A 社 Financial Agents | 本项目 |
|---|---|---|
| 平台依赖 | 主要依赖 Claude Cowork、Claude Code plugin 或 Managed Agents | 基于 Python、LangGraph 和本地文件系统；模型走 OpenAI-compatible gateway，默认 DashScope/Qwen，可替换 |
| 市场覆盖 | 偏全球金融机构通用流程 | 原生面向 A 股、港股、中概、中国宏观、公告、北向/南向、ETF、龙虎榜、期指和财报季 |
| 数据来源 | 侧重海外金融数据连接器和企业数据权限 | 已配置同花顺 iFind MCP，覆盖股票、基金、宏观、新闻、债券、全球股票和指数 |
| 投研逻辑 | 更像技能和模板集合 | 按二级市场投研链路组织：盘前 -> 行业/主题 -> 筛选 -> thesis -> 单股覆盖 -> 三表 -> 估值 -> 图表/报告 |
| 产出形态 | 偏企业工作流和 Office 审阅 | 直接输出 Markdown、JSON、Excel、PPT、PNG 图表和最终综合报告 |
| 可复盘性 | 平台日志为主 | artifacts 全量落盘，包含 source log、run manifest、model audit、valuation state 等 |

一句话：A 社强在“企业级通用金融模板”，这个项目强在“面向中国股票投研的本地生产系统”。

## 3. 公开案例

我只保留 3 个最能代表能力边界的样例，已经放到 `docs/examples/`，推到 GitHub 后可以直接打开：

| 案例 | 链接 | 代表能力 |
|---|---|---|
| 盘前晨报 | [A 股开盘前 Morning Note](docs/examples/a-share-morning-note.md) | 隔夜市场、政策、公告、资金面和当日交易主线 |
| 行业研究 | [MLCC 行业综合研究](docs/examples/mlcc-sector-research.md) | 行业供需、价值链、竞争格局、重点标的和风险变量 |
| 单股研究 | [陕西煤业公司研究](docs/examples/shaanxi-coal-company-research.md) | 公司身份、业务模式、成本结构、治理、护城河和风险 |

## 4. 配置方法

环境要求：

- Python 3.11
- OpenAI-compatible 模型网关，默认 `https://dashscope.aliyuncs.com/compatible-mode`
- 同花顺 iFind MCP token 或完整 Authorization header

安装：

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ./DCF-builder -e ./industry-ananlysis -e ./morning-note \
  -e ./screen -e ./sector -e ./thesis -e ./orchestrator \
  -e ./single-stock-coverage
```

配置：

```bash
cp .env.example .env
```

`.env` 中至少填写：

```bash
MODEL_GATEWAY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
MODEL_GATEWAY_API_KEY=...
MODEL_NAME=qwen-3.7-max
MODEL_MAX_TOKENS=16000

# 二选一
IFIND_MCP_TOKEN=...
IFIND_MCP_AUTHORIZATION=Bearer ...
```

同花顺 iFind MCP URL 已写入各子项目 `config.yaml`：

| Server | URL |
|---|---|
| `ifind-stock` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-stock-mcp` |
| `ifind-fund` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-fund-mcp` |
| `ifind-edb` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-edb-mcp` |
| `ifind-news` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-news-mcp` |
| `ifind-bond` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-bond-mcp` |
| `ifind-global-stock` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-global-stock-mcp` |
| `ifind-index` | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-index-mcp` |

运行：

```bash
.venv/bin/langgraph dev
```

常用 graph：`deep_orchestrator`、`morning_note`、`market_researcher`、`sector_research`、`stock_screen`、`thesis_tracker`、`single_stock_coverage`、`dcf_builder`。

## 5. 当前版本、迭代方向和联系

当前版本：`v0.1 research-preview`，截至 2026-06-21。

已具备：

- 顶层 orchestrator 和核心投研 agent
- 同花顺 iFind MCP 统一数据接入
- 晨报、行业研究、资金扫描、公告扫描、thesis、单股覆盖、三表模型、DCF 和图表包
- 本地 Markdown / JSON / Excel / PPT / PNG artifacts 输出

下一步：

- polish 单股覆盖最终报告
- 稳定股票筛选和 watchlist 解释
- 标准化 source log、引用和公开样例库
- 增加组合跟踪、回测和 thesis scorecard 自动更新

联系：

- 邮箱：huang.shengsong1@gmail.com
- 问题和需求：请在当前项目提交 issue
