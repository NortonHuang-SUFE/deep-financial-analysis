---
name: sector-overview
description: "Create China-focused industry and sector landscape reports covering industry classification, market size, value chain, policy/regulation, listed-company competition, financial and valuation comparison, and investment implications. Use for \"行业研究\", \"赛道分析\", \"sector overview\", \"industry report\", \"market landscape\", \"行业深度\", \"产业链分析\", or thematic China equity research."
tags:
  - research
  - sector-analysis
  - china-equity
---

# Sector Overview

## Workflow

### Step 1: Define Scope

- **行业/赛道边界**：明确一级/二级/三级行业或主题赛道，优先映射申万、中信、国证等分类；说明自定义口径和排除项。
- **研究目的**：投资备忘录、行业初始覆盖、主题研究、公司池筛选、客户材料或内部知识建设。
- **市场范围**：中国大陆、港股相关中国资产、全球可比市场；注明 A 股、港股、未上市主体是否纳入。
- **深度和格式**：简报、完整 Markdown 报告、数据 JSON 附件；如用户未指定，默认完整 Markdown 报告。
- **时间口径**：明确数据截至日期，历史期和预测期分别标注。

### Step 2: Data Plan and Source Discipline

- 优先调用 iFind：股票、指数、新闻、EDB、基金、债券、全球股票等 MCP 工具。
- 对市场规模、价格、产量、销量、进出口、行业利润、公司财务、估值、政策事件建立来源清单。
- 监管和政策优先查国务院、发改委、工信部、财政部、商务部、生态环境部、证监会、交易所、行业主管部门、地方政府和行业协会。
- 无法核验的数据、估算或模型常识必须标 `[UNSOURCED]`；不要用精确数字暗示确定性。

### Step 3: Industry Definition and Market Overview

**分类与边界**
- 申万/中信/国证分类对应关系。
- 与港股、全球行业分类或主题指数口径的差异。
- 产业链环节和收入确认方式。

**市场规模与增长**
- 行业收入/产量/销量/装机/用户数/交易额等最贴近行业的规模指标。
- 近 3-5 年增长率、周期位置、价格和库存变化。
- 未来增长假设：需求端、供给端、政策端、技术端分别说明。
- 细分市场：产品、区域、客户、应用场景、渠道。

**行业结构**
- 集中度和头部份额，尽量给 CR3/CR5/CR10。
- 进入壁垒：资本、技术、客户认证、渠道、牌照、资源、能耗/环保约束。
- 盈利机制：价格传导、成本曲线、规模效应、资产周转、补贴或税收优惠。

### Step 4: China-Specific Policy and Regulation

- 中央政策：产业规划、准入限制、集采、医保/药监/金融监管、出口管制、反垄断、数据安全。
- 地方政策：招商补贴、税收优惠、土地/电价/能耗指标、产业基金、地方国资参与。
- 供给约束：产能置换、能耗双控、环保安监、牌照审批、进口替代。
- 政策影响：谁受益、谁承压、影响财务报表的路径和时间滞后。

### Step 5: Value Chain and Competitive Landscape

**产业链图谱**
- 上游：原材料、核心零部件、设备、能源、技术 IP。
- 中游：制造、运营、平台、服务或加工环节。
- 下游：客户结构、渠道、终端需求、议价能力。
- 关键瓶颈：国产化率、供应安全、价格波动、产能周期。

**公司池**

| 公司 | 市场 | 代码 | 环节 | 收入/利润口径 | 市占率 | 核心优势 | 主要风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

公司覆盖建议：
- A 股和港股上市公司优先，必要时加入重要未上市、国企或外资公司。
- 对头部 5-10 家公司写 2-3 句定位：主营、环节、护城河、近期变化。
- 标出份额提升/丢失者，并解释原因。

### Step 6: Financial and Valuation Comparison

- 财务：收入、归母净利润、毛利率、净利率、ROE、经营现金流、资本开支、研发费用率。
- 估值：PE、PB、PS、EV/EBITDA、股息率或行业适用指标；比较当前、历史区间和市场/指数相对位置。
- 对周期行业补充价格、库存、产能利用率和吨/单位盈利；对成长行业补充渗透率、研发、订单、留存或客户指标。
- 解释估值溢价/折价来源：成长、盈利质量、政策风险、龙头地位、治理、流动性。

### Step 7: Investment Implications

- 先给 3-5 条可行动结论：最重要变量、受益链条、龙头/弹性标的、回避方向。
- 牛熊分歧：需求、价格、政策、竞争、估值各列关键争议。
- 催化剂：政策落地、财报、订单、价格拐点、行业会议、招标/集采、出口数据。
- 风险：政策反转、补贴退坡、价格战、产能过剩、技术替代、监管处罚、汇率/贸易摩擦。

### Step 8: Output Artifacts

- 使用 `create_task_output_dir` 确认输出目录。
- 使用 `write_markdown_report` 写最终报告。
- 使用 `write_json_artifact` 保存结构化公司池、关键指标、来源清单或未来源化假设清单。
- 输出目录在 workspace 根目录 `out/<YYYYMMDD-HHMMSS>/`；同一次任务复用同一个时间戳目录。

## Quality Bar

- 不把 TAM 叙事当作现实市场规模；区分当前市场、可服务市场和远期空间。
- 表格中每个关键数字都要有来源或 `[UNSOURCED]`。
- 结论必须能追溯到数据、政策或公司事实。
- 研究报告会快速过期，必须注明截至日期。

