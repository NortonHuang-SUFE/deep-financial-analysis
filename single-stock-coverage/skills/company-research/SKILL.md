---
name: company-research
description: "Run Task 1 company research for single-stock coverage. Use for single-company equity research that must produce company_research.md, business_driver_map.json, and source_log.json with China A/H-share source discipline and business-driver mapping for later financial modeling and valuation tasks."
tags:
  - research
  - equity-research
  - single-stock-coverage
---

# Company Research

本 skill 用于 `single-stock-coverage` 的 Task 1。默认用中文输出研究结论；JSON 字段名使用英文键名，尤其保留 `ticker`、`company`、`source`。

## Workflow

### Step 1: 确认标的和输出目录

- 确认 `company`、`ticker`、`market`、交易所、币种、财年、上市状态和主要会计准则。
- 若标的不明确，最多问一个澄清问题；若只是行业或主题请求，交回外层 agent。
- 在本次任务目录下创建或使用：

```text
01_company_research/
  company_research.md
  business_driver_map.json
  source_log.json
```

- 不创建额外完成摘要、估值文件、模型文件或最终报告。

### Step 2: Source Plan and Evidence Gate

优先级从高到低：

1. 公司一手披露：年报、中报、季报、招股书、公告、交易所文件、IR 演示、业绩会 transcript。
2. 监管和交易所：证监会、上交所、深交所、北交所、港交所、联交所披露易、行业主管部门、地方政府。
3. 经营和行业数据：公司官网、客户/供应商公告、行业协会、统计局/部委、可信数据库、iFind 工具结果。
4. 二手来源：新闻、卖方研报、行业研究、专家访谈纪要；只能作为辅助证据或交叉验证。

要求：

- 为每个来源分配稳定 `source_id`，格式建议 `SRC-001`。
- 正文和 JSON 中的关键事实使用 `source_id` 引用。
- 记录发布日期、访问日期、口径、URL 或本地文件路径。
- 无法核验的信息必须同句标注 `[UNSOURCED]`，并进入 `source_log.json.unsourced_claims`。
- 不混用公司/集团/分部、A 股/H 股/ADR、人民币/港币/美元、自然年/财年、合并/母公司口径。

### Step 3: 公司身份与业务模式

覆盖：

- 基本身份：`company`、`ticker`、市场、交易所、行业分类、总部、上市日期、财年、币种、会计准则。
- 业务结构：产品/服务、分部、区域、客户类型、渠道、收入确认、价格/销量、订单/合同/续费机制。
- 规模和高层财务事实：收入、利润、毛利率、经营现金流、员工、产能、门店/用户/客户等最能解释业务的指标。
- 商业模式质量：复购、客户集中度、议价能力、成本传导、经营杠杆、资本密集度、周期性。

### Step 4: 管理层、股权和治理

- 管理层：CEO、CFO 和 1-2 名关键业务负责人；记录履历、任期、过往成绩和潜在关键人风险。
- 股权结构：控股股东、实控人、国资或地方政府背景、机构持股、员工激励、股权质押。
- 治理风险：关联交易、同业竞争、资金占用、审计意见、内部控制、监管处罚、问询函或诉讼。
- 激励约束：薪酬、期权/股权激励、业绩考核目标、回购、增减持安排。

### Step 5: 竞争格局和直接行业影响

- 识别 5-10 个直接竞争者、替代品或潜在进入者；A/H 股公司优先，必要时加入未上市、国企、外资或全球可比公司。
- 比较维度包括产品、价格、渠道、客户、技术、成本、产能、品牌、份额、盈利能力和资本实力。
- 行业/主题内容只纳入与标的直接相关的信息：需求、价格、成本、供给、政策、技术路线、库存周期、渠道、融资环境。
- 对每个行业或政策变量写清传导路径：影响收入、毛利率、费用率、CapEx、营运资本、风险或催化剂中的哪一项。

### Step 6: A/H 股制度检查

按适用市场检查，不适用也要简短说明：

- A 股：业绩预告/快报、问询函/监管函、ST/退市风险、停复牌、涨跌停、限售解禁、减持规则、融资融券、再融资、重大资产重组、股权质押、北向资金、地方国资和产业政策。
- 港股：盈利警告/喜讯、港交所公告、港股通、南向资金、回购和库存股、配售/供股、H 股全流通、不同投票权、做空披露、流动性折价。
- 多地上市：ticker、币种、股本、交易日、会计准则、披露文件和 A/H 溢折价必须分开。

### Step 7: 风险、催化剂和可证伪指标

风险至少覆盖：

- 基本面：需求、价格、份额、客户集中、供应链、技术替代。
- 财务质量：利润率、现金流、债务、应收/存货、资本开支、减值。
- 治理与监管：实控人、关联交易、处罚、政策变化、牌照或合规。
- 交易和市场：流动性、解禁/减持、港股通/指数调整、汇率、利率和商品价格。

催化剂至少考虑：

- 财报、业绩预告/快报、经营数据、订单、价格、产能、产品发布、政策落地、回购、增减持、指数和港股通调整。

每项风险和催化剂都要绑定可跟踪指标、触发条件、可能影响方向和来源。

### Step 8: 写入 `company_research.md`

建议结构：

```markdown
# Company Research - {company} ({ticker})

## 1. 标的摘要
## 2. 公司身份与上市信息
## 3. 业务模式与收入结构
## 4. 产品、客户、渠道和区域
## 5. 成本、利润率和经营杠杆
## 6. 管理层、股权结构与治理
## 7. 竞争格局与护城河
## 8. 行业/政策/主题对标的的直接影响
## 9. 风险与证伪指标
## 10. 催化剂与后续跟踪变量
## 11. 待核验事项和 [UNSOURCED] 列表
## 12. 来源索引
```

正文必须结论先行、事实可追溯。表格中的关键数字同样需要 `source_id` 或 `[UNSOURCED]`。

### Step 9: 写入 `business_driver_map.json`

目标是把业务事实转成 Task 2/3 可消费的驱动变量。JSON 必须能被解析，不要写注释。

推荐 schema：

```json
{
  "company": "Company name",
  "ticker": "000000.SZ",
  "market": "A-share",
  "currency": "CNY",
  "fiscal_year_end": "12-31",
  "source_cutoff_date": "YYYY-MM-DD",
  "generated_at": "YYYY-MM-DD",
  "driver_summary": {
    "top_revenue_drivers": ["..."],
    "top_margin_drivers": ["..."],
    "top_risk_drivers": ["..."],
    "top_catalysts": ["..."]
  },
  "revenue_drivers": [
    {
      "driver_id": "REV-001",
      "name": "Segment volume growth",
      "business_fact": "Fact stated in Chinese or English",
      "mechanism": "How this changes revenue",
      "model_line_item": "Revenue Build / Segment A revenue",
      "direction": "positive|negative|mixed|unknown",
      "horizon": "near_term|medium_term|long_term",
      "tracking_metrics": ["volume", "price", "market share"],
      "sensitivity": "high|medium|low|unknown",
      "source_ids": ["SRC-001"],
      "confidence": "high|medium|low",
      "update_triggers": ["..."],
      "notes": ""
    }
  ],
  "margin_drivers": [
    {
      "driver_id": "MAR-001",
      "name": "Gross margin driver",
      "business_fact": "",
      "mechanism": "",
      "model_line_item": "Income Statement / Gross margin",
      "direction": "positive|negative|mixed|unknown",
      "horizon": "near_term|medium_term|long_term",
      "tracking_metrics": [],
      "sensitivity": "high|medium|low|unknown",
      "source_ids": [],
      "confidence": "high|medium|low",
      "update_triggers": [],
      "notes": ""
    }
  ],
  "capex_drivers": [
    {
      "driver_id": "CAPEX-001",
      "name": "Capacity expansion",
      "business_fact": "",
      "mechanism": "",
      "model_line_item": "PP&E / CapEx",
      "direction": "increase|decrease|mixed|unknown",
      "horizon": "near_term|medium_term|long_term",
      "tracking_metrics": [],
      "sensitivity": "high|medium|low|unknown",
      "source_ids": [],
      "confidence": "high|medium|low",
      "update_triggers": [],
      "notes": ""
    }
  ],
  "working_capital_drivers": [
    {
      "driver_id": "WC-001",
      "name": "Receivables or inventory cycle",
      "business_fact": "",
      "mechanism": "",
      "model_line_item": "Working Capital / DSO DIO DPO",
      "direction": "improves_cash|uses_cash|mixed|unknown",
      "horizon": "near_term|medium_term|long_term",
      "tracking_metrics": [],
      "sensitivity": "high|medium|low|unknown",
      "source_ids": [],
      "confidence": "high|medium|low",
      "update_triggers": [],
      "notes": ""
    }
  ],
  "risk_drivers": [
    {
      "driver_id": "RISK-001",
      "name": "Risk name",
      "risk_type": "fundamental|financial_quality|governance|regulatory|liquidity|market",
      "business_fact": "",
      "mechanism": "",
      "affected_model_items": ["Revenue", "Gross margin"],
      "severity": "high|medium|low",
      "likelihood": "high|medium|low|unknown",
      "early_warning_indicators": [],
      "source_ids": [],
      "confidence": "high|medium|low",
      "notes": ""
    }
  ],
  "catalyst_drivers": [
    {
      "driver_id": "CAT-001",
      "name": "Catalyst name",
      "catalyst_type": "earnings|guidance|policy|price|order|capacity|buyback|shareholding|index|stock_connect|other",
      "expected_timing": "YYYY-QX or date if known",
      "business_fact": "",
      "mechanism": "",
      "potential_impact": "positive|negative|mixed|unknown",
      "affected_model_items": [],
      "tracking_metrics": [],
      "source_ids": [],
      "confidence": "high|medium|low",
      "notes": ""
    }
  ],
  "unsourced_claims": [
    {
      "claim": "",
      "location": "company_research.md section or driver_id",
      "reason": "Why source is missing",
      "needed_source": "Expected source to verify"
    }
  ]
}
```

最少要求：

- 六类 driver 数组必须存在；没有发现明确 driver 时使用空数组并在 `notes` 或 `unsourced_claims` 解释。
- 每个非空 driver 必须有 `driver_id`、`name`、`business_fact`、`mechanism`、`model_line_item` 或 `affected_model_items`、`source_ids`、`confidence`。
- `source_ids` 必须能在 `source_log.json.sources` 中找到；若没有来源，正文和对应 driver 均标 `[UNSOURCED]`。

### Step 10: 写入 `source_log.json`

推荐 schema：

```json
{
  "company": "Company name",
  "ticker": "000000.SZ",
  "market": "A-share",
  "source_cutoff_date": "YYYY-MM-DD",
  "generated_at": "YYYY-MM-DD",
  "sources": [
    {
      "source_id": "SRC-001",
      "source": "Company annual report",
      "source_type": "annual_report|interim_report|quarterly_report|filing|exchange_announcement|transcript|investor_presentation|regulator|industry_data|news|sell_side|website|database|other",
      "title": "",
      "publisher": "",
      "published_at": "YYYY-MM-DD",
      "accessed_at": "YYYY-MM-DD",
      "url": "",
      "file_path": "",
      "market": "A-share",
      "reliability": "primary|official|secondary|low",
      "used_in": ["company_research.md#section", "business_driver_map.json#REV-001"],
      "key_facts": ["..."],
      "notes": ""
    }
  ],
  "unsourced_claims": [
    {
      "claim": "",
      "location": "",
      "reason": "",
      "needed_source": ""
    }
  ],
  "source_gaps": [
    {
      "topic": "",
      "why_it_matters": "",
      "suggested_source": ""
    }
  ]
}
```

要求：

- `sources` 覆盖正文和 driver map 中引用的全部 `source_id`。
- 每个来源记录至少包含 `source_id`、`source`、`source_type`、`title` 或 URL/文件名、`published_at` 或 `accessed_at`、`reliability`、`used_in`。
- 同一事实来自多个来源时全部记录；冲突时在 `notes` 说明口径差异。
- `unsourced_claims` 和 `source_gaps` 可为空数组，但字段必须存在。

## Quality Checklist

完成前逐项检查：

- [ ] 标的唯一：`company`、`ticker`、市场、币种、财年和会计准则明确。
- [ ] 三个指定文件已写入 `01_company_research/`，且没有额外 Task 1 artifact。
- [ ] `company_research.md` 默认中文；关键数字、事件和判断有 `source_id` 或 `[UNSOURCED]`。
- [ ] `business_driver_map.json` 是合法 JSON，六类 driver 数组齐全。
- [ ] 每个 driver 都说明业务事实、财务传导机制、模型项目、来源和信心等级。
- [ ] `source_log.json` 是合法 JSON，所有 `source_ids` 都可回查。
- [ ] A 股、港股或多地上市制度因素已检查；不适用时已说明。
- [ ] 行业、政策和主题内容都说明了对该标的的直接传导路径。
- [ ] 风险和催化剂都绑定可跟踪指标或触发条件。
- [ ] 明确列出待核验事项、来源缺口和 `[UNSOURCED]`。
- [ ] 未输出估值、目标价、评级、投资建议、模型文件或最终报告。

## Handoff to Later Tasks

Task 2 主要消费：

- `business_driver_map.json.revenue_drivers`
- `margin_drivers`
- `capex_drivers`
- `working_capital_drivers`
- `company_research.md` 中的业务结构、收入确认、客户和渠道信息

Task 3 主要消费：

- `risk_drivers`
- `catalyst_drivers`
- 可证伪指标、竞争格局、政策传导和 source gaps

如证据不足以支持后续建模或估值，必须在 `company_research.md` 和 `source_log.json.source_gaps` 中明确写出缺口。
