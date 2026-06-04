# Single Stock Coverage Agent 规划与 Checklist

## 一句话定位

建设一个外层 agent 可调用的 `single-stock-coverage` 复杂 subagent。它不负责行业/主题持续跟踪，只负责围绕单一个股完成首次覆盖、事件更新、模型刷新、估值判断和报告落盘。

核心主轴严格沿用原始 `initiating-coverage` 的 5-task workflow；估值方法必须复用 `valuation-methodologies`。

关键参考：

- `../financialServices/plugins/vertical-plugins/equity-research/skills/initiating-coverage/SKILL.md`
- `../financialServices/plugins/vertical-plugins/equity-research/skills/initiating-coverage/references/valuation-methodologies.md`
- `../financialServices/plugins/vertical-plugins/equity-research/skills/initiating-coverage/references/task3-valuation.md`
- `../financialServices/plugins/vertical-plugins/financial-analysis/skills/3-statement-model/SKILL.md`
- `../financialServices/plugins/vertical-plugins/financial-analysis/skills/dcf-model/SKILL.md`
- `../financialServices/plugins/vertical-plugins/financial-analysis/skills/audit-xls/SKILL.md`
- `../financialServices/plugins/vertical-plugins/financial-analysis/skills/xlsx-author/SKILL.md`
- `../financialServices/plugins/vertical-plugins/equity-research/skills/model-update/SKILL.md`

## 整体架构

```text
outer_agent
  -> single_stock_coverage_agent
       -> task1_company_research_subagent
       -> task2_financial_model_subagent
       -> task3_valuation_subagent
            -> dcf_execution / current DCF-builder capability
       -> task4_chart_pack_subagent
       -> task5_report_assembly_subagent
       -> update_router + coverage_state_manager
```

顶层 `single_stock_coverage_agent` 只做：

- 任务识别
- 依赖检查
- subagent 编排
- 状态更新
- 文件索引
- 最终合成

行业/主题观点由外层 agent 传入；本 agent 只判断“这些信息如何影响这个标的”。

## 5-Task Workflow

| Task | 目标 | 关键产出 |
| --- | --- | --- |
| Task 1 Company Research | 搞清公司如何赚钱、关键变量、竞争、风险、催化剂 | `company_research.md`、`business_driver_map.json` |
| Task 2 Financial Modeling | 构建三张表、收入 build、经营预测、DCF inputs | `integrated_model.xlsx`、`financial_facts.json`、`model_audit.md` |
| Task 3 Valuation Analysis | 形成、审计、执行、交叉验证估值假设 | `assumption_pack.md`、`assumption_audit.md`、`dcf_model.xlsx`、`valuation_analysis.md` |
| Task 4 Chart Generation | 把 Task 1-3 的结论图表化 | `chart_pack/`、`chart_index.json` |
| Task 5 Report Assembly | 组装 initiation report 或 update memo | `final_report.md/.docx` |

## Task 1 Company Research

Task 1 负责回答：公司到底如何赚钱，未来价值由哪些变量驱动，哪些事实会推翻当前投资逻辑。

核心内容：

- 公司身份：名称、ticker、市场、行业、币种、财年、上市状态。
- 业务模式：产品、区域、客户、渠道、价格/销量、收入确认。
- 管理层和治理：管理层背景、股权结构、激励、治理风险。
- 竞争格局：直接竞争者、替代品、份额变化、护城河。
- 行业与政策对个股的影响：只吸收与标的直接相关的行业/主题信息。
- 风险：基本面、财务质量、治理、监管、流动性、估值。
- 催化剂：财报、业绩预告、政策、价格、订单、产能、回购、减持、指数/港股通调整。

关键输出：

```text
01_company_research/
  company_research.md
  business_driver_map.json
  source_log.json
```

`business_driver_map.json` 应把业务事实转成后续模型变量：

- revenue drivers
- margin drivers
- capex drivers
- working capital drivers
- risk drivers
- catalyst drivers

## Task 2 Financial Modeling

Task 2 不是简单历史财务提取，必须参考 `3-statement-model` 构建 integrated model。

建议 workbook tabs：

```text
Cover
Sources
Assumptions
Revenue Build
Income Statement
Balance Sheet
Cash Flow Statement
Working Capital
PP&E / D&A
Debt / Interest
Share Count
DCF Inputs
Checks
```

强制原则：

- 预测、联动、subtotal、check 全部用 Excel 公式。
- 只有历史数据和假设驱动可以硬编码，且必须带来源。
- 必须有 BS balance、cash tie-out、NI link、RE roll-forward、CapEx/PP&E tie、debt tie。
- 所有 workbook 必须跑 `audit-xls`。
- 三表输出必须能支持 Task 3 DCF inputs。

关键输出：

```text
02_financial_model/
  integrated_model.xlsx
  financial_facts.json
  model_audit.md
```

`financial_facts.json` 至少包含：

- historical revenue, EBIT, EBITDA, net income
- D&A, CapEx, NWC change
- debt, cash, shares
- segment revenue and margin if available
- model projection summary
- source strings and `[UNSOURCED]` list

## Task 3 Valuation Analysis

估值模块不等于 DCF-builder。DCF 只是执行器。Task 3 的中心是 assumption system。

### 第一性原理

DCF 建模的重点不是把模型跑出来，而是回答三个问题：

1. 假设是否在有足够信息的基础上进行？
2. 假设是否有逻辑？
3. 假设做出是否正确？

这里的“正确”不是预测绝对准确，而是：

- 与历史数据一致，或解释了为什么不一致。
- 与同业区间一致，或解释了为什么应该溢价/折价。
- 与管理层指引、行业数据、政策、事件证据相互印证。
- 能被证伪。
- 通过敏感性和情景压力测试。

### Task 3 六步流程

| Step | 名称 | 作用 |
| --- | --- | --- |
| 3.1 | Evidence Gate | 检查 Task 1/2 是否足够支撑估值 |
| 3.2 | Value Driver Map | 把业务变量映射到收入、利润率、CapEx、NWC、WACC、终值 |
| 3.3 | Assumption Generation | 生成 Bear/Base/Bull 假设 |
| 3.4 | Assumption Audit | 质疑假设是否有证据、有逻辑、可验证 |
| 3.5 | Model Execution | 复用当前跑得顺的 DCF-builder 能力生成模型 |
| 3.6 | Valuation Reconciliation | 用 DCF、trading comps、precedent transactions、历史估值和市场隐含预期交叉验证 |

### valuation-methodologies 的复用方式

`valuation-methodologies` 必须成为 Task 3 的核心参考，要求：

- DCF：内在价值主方法。
- Trading comps：市场相对估值。
- Precedent transactions：若行业 M&A 相关，作为控制权价值参考。
- 必须给 valuation range，不只给点估值。
- 必须解释方法权重。
- 必须做 sanity checks：历史倍数、同业溢价/折价、市场隐含增长、IRR、market cap 合理性。

### DCF 与三表关系

DCF 不应替代三表。DCF 应吃三表输出：

- Revenue 来自 `Revenue Build`。
- EBIT / tax 来自 Income Statement。
- D&A 来自 PP&E / D&A schedule。
- CapEx 来自 Cash Flow 或 PP&E schedule。
- NWC 来自 Working Capital。
- Debt、cash、shares 来自 Balance Sheet / Share Count。
- WACC、terminal growth、scenario assumptions 来自 assumption system。

当前 `DCF-builder` 可以继续作为 Step 3.5 的成熟执行器复用：comps、DCF workbook、validation、valuation summary 都可以保留。但它的上游应由新的 assumption pipeline 控制。

### Task 3 输出结构

```text
03_valuation/
  evidence_sufficiency.md
  value_driver_map.json
  assumption_pack.md
  assumption_audit.md
  dcf_model.xlsx
  comps.xlsx
  precedent_transactions.xlsx  # if applicable
  valuation_analysis.md
  valuation_state.json
```

`assumption_pack.md` 是核心产物，建议结构：

```markdown
## 1. 估值结论
## 2. 信息基础与缺口
## 3. 价值驱动树
## 4. Bear/Base/Bull 假设
## 5. 假设逻辑
## 6. 假设审计
## 7. DCF 输出
## 8. 估值方法交叉验证
## 9. 可证伪指标与后续跟踪
```

### Assumption Audit 检查表

- [ ] 收入假设是否来自产品/区域/客户/价格/销量拆分。
- [ ] Base case 是否贴近可验证的经营路径，而不是机械 CAGR。
- [ ] Bear case 是否体现真实压力，而不是轻微下调。
- [ ] Bull case 是否有产能、需求、价格或份额证据支持。
- [ ] EBIT margin 是否与历史、同业、规模效应一致。
- [ ] CapEx 是否与增长、产能、维护性投资匹配。
- [ ] NWC 是否与商业模式、账期、库存周期匹配。
- [ ] WACC 是否使用市场价值资本结构，而非账面值。
- [ ] Terminal growth 是否低于 WACC，并符合行业成熟度。
- [ ] Terminal value 占 EV 是否过高并被解释。
- [ ] DCF 结果是否与 comps、历史区间、市场隐含预期冲突；冲突是否解释。

### Valuation Reconciliation 要求

必须形成一张方法论汇总表：

| Method | Low | Base | High | Weight | Rationale |
| --- | --- | --- | --- | --- | --- |
| DCF | | | | | |
| Trading Comps | | | | | |
| Precedent Transactions | | | | | |
| Historical Multiples | | | | | |
| Market-Implied Check | | | | | |

权重原则：

- DCF：当 Task 1/2 信息充分、预测可靠时权重更高。
- Trading comps：当 peer set 足够干净、市场定价有效时权重更高。
- Precedent transactions：只有 M&A 相关性高时纳入主要权重。
- Historical multiples：主要做 sanity check。
- Market-implied check：主要用于判断市场已经 pricing in 什么。

## Task 4 Chart Generation

Task 4 只基于 Task 1-3 的已落盘事实和估值输出生成图表，不重新研究。

关键图表：

- revenue by segment
- revenue / EBIT / FCF trend
- margin bridge
- scenario comparison
- DCF sensitivity
- valuation football field
- comps multiple comparison
- historical valuation multiples
- catalyst timeline
- risk matrix

关键输出：

```text
04_charts/
  chart_pack/
  chart_index.json
```

## Task 5 Report Assembly

Task 5 组装最终 initiation report 或 update memo。

原则：

- 不重新创造新结论。
- 引用 Task 1-4 的文件和图表。
- 保持结论、目标价、假设、风险、催化剂一致。
- initiation report 可以完整；事件更新 memo 应只强调 delta。

关键输出：

```text
05_report/
  final_report.md
  final_report.docx  # optional
  source_index.json
```

## 事件后更新路由

事件更新不机械重跑完整 initiation，而是只重跑受影响 task。

| 事件 | 重跑范围 |
| --- | --- |
| 财报/业绩快报 | Task 2 model-update -> Task 3 valuation -> update memo |
| 指引变化 | Task 2 assumptions update -> Task 3 |
| 股价大幅变化 | Task 3 valuation refresh |
| 重大订单/产能/价格 | Task 1 delta -> Task 2 if numbers change -> Task 3 |
| 政策/监管/处罚 | Task 1 delta -> Task 3 assumption audit -> thesis impact |
| 模型出错 | `audit-xls` -> fix checklist |
| 财报前 | earnings-preview -> scenario/watch items |

每次更新都必须输出 delta：

- 新事件是什么。
- 影响哪个 value driver 或 thesis pillar。
- 哪些模型假设改变。
- 目标价/评级/组合动作是否改变。
- 哪些数据仍 `[UNSOURCED]`。

## 通用 Skills 抽象

| Skill | 用途 |
| --- | --- |
| `coverage-state` | 读取/更新覆盖档案、run manifest、artifact index |
| `company-research` | 从 initiating coverage Task 1 抽象 |
| `financial-data-normalization` | 清洗、统一口径、来源化历史数据 |
| `3-statement-model` | 三张表建模 |
| `model-update` | 财报、指引、宏观或事件后的模型刷新 |
| `xlsx-author` | headless workbook 生成 |
| `audit-xls` | 所有 Excel artifact 强制审计 |
| `valuation-methodologies` | DCF、comps、precedent、reconciliation 方法论 |
| `dcf-assumption-generation` | 生成 Bear/Base/Bull DCF inputs |
| `assumption-audit` | 红队质疑估值假设 |
| `valuation-reconciliation` | 多方法估值区间、权重、sanity checks |
| `chart-pack` | Task 4 图表生成 |
| `report-assembly` | Task 5 报告组装 |

## 落盘契约

```text
coverage/{market}-{ticker}/
  coverage_state.json
  runs/{YYYYMMDD-HHMMSS}/
    run_manifest.json
    01_company_research/
      company_research.md
      business_driver_map.json
      source_log.json
    02_financial_model/
      integrated_model.xlsx
      financial_facts.json
      model_audit.md
    03_valuation/
      evidence_sufficiency.md
      value_driver_map.json
      assumption_pack.md
      assumption_audit.md
      dcf_model.xlsx
      comps.xlsx
      precedent_transactions.xlsx
      valuation_analysis.md
      valuation_state.json
    04_charts/
      chart_pack/
      chart_index.json
    05_report/
      final_report.md
      final_report.docx
      source_index.json
```

`run_manifest.json` 至少记录：

- run id
- ticker / market / company
- task type: initiation / update / valuation refresh / model audit
- triggering event
- subagents called
- input artifact paths
- output artifact paths
- final conclusion
- `[UNSOURCED]` list
- follow-up checklist

`coverage_state.json` 至少记录：

- latest company identity
- latest coverage status
- latest model path
- latest valuation state
- latest price target / rating / recommendation
- latest thesis pillars
- key assumptions
- next catalysts
- stale data flags

## 开发 Checklist

- [ ] 新建 `single_stock_coverage_agent`，明确只做个股覆盖。
- [ ] 按 initiating coverage 写 5-task 状态机。
- [ ] 定义 `coverage_state.json`、`run_manifest.json` schema。
- [ ] 实现 Task 1 输出 `business_driver_map.json`。
- [ ] 实现 Task 2 integrated three-statement model。
- [ ] 抽象并接入 `model-update`、`xlsx-author`、`audit-xls`。
- [ ] 重构 Task 3 为 valuation assumption system。
- [ ] 将 `valuation-methodologies` 固化为 Task 3 必读参考。
- [ ] 复用当前 DCF-builder 作为 `dcf_execution`。
- [ ] 新建 `assumption-audit` 和 `valuation-reconciliation` skills。
- [ ] 所有 valuation 必须先产出 `assumption_pack.md` 和 `assumption_audit.md`。
- [ ] 所有 Excel 必须产出 audit report。
- [ ] 支持事件更新只重跑受影响 task。
- [ ] 增加 routing tests：首次覆盖、财报更新、指引变化、重大公告、估值刷新、模型审计。
- [ ] 增加 artifact tests：每次 run 必须完整落盘，下一次更新能读取前次 state。

## 最终原则

以 `initiating-coverage` 为流程骨架，以三张表为财务基础，以 `valuation-methodologies` 为估值方法论，以 assumption quality control 为 Task 3 核心，以现有 DCF-builder 作为成熟执行器复用。
