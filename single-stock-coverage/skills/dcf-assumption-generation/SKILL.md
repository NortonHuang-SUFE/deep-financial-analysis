---
name: dcf-assumption-generation
description: Generates evidence-based Bear/Base/Bull valuation assumptions for Task 3 from Task 1 business drivers, Task 2 financial facts, peer data, and market evidence.
---

# DCF Assumption Generation

Use this skill after the Task 3 Evidence Gate and Value Driver Map are complete.
The goal is to create an auditable assumption pack that controls DCF execution
and supports valuation reconciliation.

This skill adapts the mature DCF assumption workflow from `DCF-builder`, but in
single-stock coverage it sits inside the broader Task 3 assumption system.
DCF is one model executor; assumptions must be generated from evidence first.

## Inputs

Required inputs:

- `evidence_sufficiency.md`
- `value_driver_map.json`
- `01_company_research/company_research.md`
- `01_company_research/business_driver_map.json`
- `02_financial_model/integrated_model.xlsx`
- `02_financial_model/financial_facts.json`
- `02_financial_model/model_audit.md`
- Peer/comps evidence already collected, if available.
- Market, industry, macro, announcement, management-guidance, policy, and event
  evidence relevant to the company.

Do not proceed if the Evidence Gate says `Do Not Proceed`.

## Workflow

1. Confirm identity and base year.
   - Company, ticker, market, currency, fiscal year end, latest historical
     period, forecast period, current price date, and units.

2. Start from business drivers.
   - Read Task 1's `business_driver_map.json`.
   - Map product, segment, region, customer, price, volume, cost, capacity,
     working-capital, leverage, policy, and catalyst drivers to model variables.

3. Build revenue from economically meaningful drivers.
   - Prefer segment/product/region/customer/volume/price build where evidence
     supports it.
   - If only partial detail exists, use sourced splits and mark the rest
     `[UNSOURCED]`.
   - Explain how segment assumptions aggregate into total revenue growth.

4. Generate Bear/Base/Bull scenarios.
   - Base case should be the most evidence-backed operating path.
   - Bear case should represent a real pressure case, not a minor haircut.
   - Bull case should require evidence such as capacity, demand, pricing,
     market-share, cost, or policy support.
   - Each scenario must include a narrative, driver assumptions, and model
     inputs.

5. Build non-revenue assumptions.
   - EBIT or EBITDA margin: tie to history, peers, scale effects, mix, pricing,
     utilization, cost inflation, and management commentary.
   - Tax rate: tie to statutory rate, historical cash/effective tax, tax
     incentives, or explicit disclosure.
   - D&A/revenue: tie to fixed asset base, CapEx history, depreciation policy,
     and peer range.
   - CapEx/revenue: separate maintenance and growth logic when possible.
   - NWC/delta revenue or days: tie to receivables, inventory, payables, channel
     model, customer concentration, and production cycle.
   - WACC: document risk-free rate, beta, ERP, cost of debt, tax shield, and
     market-value capital structure where possible.
   - Terminal growth: lower than WACC and consistent with industry maturity,
     inflation, GDP, reinvestment needs, and competitive dynamics.

6. Attach evidence and gaps.
   - Every major assumption needs source strings or a visible `[UNSOURCED]`
     label.
   - Distinguish fact, estimate, inference, and judgment.

7. Prepare audit hooks.
   - For each key assumption, state what evidence would falsify it.
   - Add audit questions for fragile assumptions.

## Required `assumption_pack.md` Structure

Write `assumption_pack.md` with exactly these top-level sections:

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

Section requirements:

- `## 1. 估值结论`: preliminary valuation view before execution, and final
  conclusion after DCF/reconciliation updates. State if pending.
- `## 2. 信息基础与缺口`: Task 1/2 inputs, source coverage, model audit status,
  current market data, and `[UNSOURCED]` gaps.
- `## 3. 价值驱动树`: business drivers mapped to revenue, margin, CapEx, NWC,
  WACC, and terminal value.
- `## 4. Bear/Base/Bull 假设`: scenario table with explicit model inputs.
- `## 5. 假设逻辑`: the main section; explain why each assumption follows from
  evidence.
- `## 6. 假设审计`: summarize audit status, issues, revisions, and residual
  risks after `assumption-audit` runs.
- `## 7. DCF 输出`: DCF implied enterprise value, equity value, price/share,
  upside/downside, terminal value share, and sensitivities after execution.
- `## 8. 估值方法交叉验证`: DCF vs. trading comps, precedent transactions,
  historical multiples, and market-implied expectations.
- `## 9. 可证伪指标与后续跟踪`: indicators that would confirm or break the
  valuation thesis.

Before model execution, sections 7 and 8 may say `Pending model execution` with
the exact fields to be filled. After execution, update them with final outputs.

## Required Scenario Fields

Include Bear/Base/Bull data for:

- Revenue growth by year, preferably with segment bridge.
- EBIT or EBITDA margin by year.
- Tax rate.
- D&A as percent of revenue.
- CapEx as percent of revenue, with maintenance/growth discussion.
- NWC as percent of delta revenue or working-capital days.
- WACC and components.
- Terminal growth and rationale.
- Terminal multiple if using exit multiple as a cross-check.
- Source strings and `[UNSOURCED]` gaps.

Use decimals or clearly labeled percentages consistently. The downstream DCF
executor must be able to populate model inputs from the tables without guessing.

## Quality Bar

- Base case must be tied to a verifiable operating path.
- Bear and Bull must be asymmetric when the business risk/reward is asymmetric.
- Assumptions must reconcile with history or explicitly explain why history is
  no longer representative.
- Assumptions must reconcile with peers or explicitly explain premium/discount.
- Growth must be supported by investment, capacity, demand, price, or share
  logic.
- Terminal growth must be below WACC.
- Fragile assumptions must have falsifiable indicators.
