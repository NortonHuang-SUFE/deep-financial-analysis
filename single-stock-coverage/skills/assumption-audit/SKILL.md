---
name: assumption-audit
description: Red-teams Task 3 valuation assumptions for evidence quality, logic, historical and peer consistency, falsifiability, and model risk.
---

# Assumption Audit

Use this skill after `dcf-assumption-generation` creates `assumption_pack.md`
and before DCF model execution. The objective is to challenge assumptions hard
enough that the remaining valuation can be defended.

## Inputs

Required:

- `evidence_sufficiency.md`
- `value_driver_map.json`
- `assumption_pack.md`
- Task 1 company research artifacts.
- Task 2 financial model artifacts and model audit.
- Peer, market, industry, macro, management-guidance, policy, news, and
  announcement evidence used by the assumption pack.

## Audit Standard

An assumption is acceptable only if it passes at least one of these tests:

- It is directly sourced.
- It is consistent with historical company data.
- It is consistent with a relevant peer range.
- It intentionally departs from history/peers and explains why.
- It is a transparent judgment call, marked with evidence limits and
  falsifiable indicators.

## Audit Checklist

Revenue:

- Revenue assumptions come from product, segment, region, customer, price,
  volume, capacity, or market-share drivers where possible.
- Base case is a verifiable operating path, not a mechanical CAGR.
- Bear case reflects real pressure such as price decline, volume weakness,
  share loss, utilization drop, regulation, or customer/channel stress.
- Bull case has evidence from capacity, demand, pricing, share gains, orders,
  backlog, policy, product cycle, or management execution.
- Segment assumptions aggregate cleanly into total revenue growth.

Margins:

- EBIT or EBITDA margin path reconciles with historical margins.
- Peer margins support the terminal or steady-state margin, or premium/discount
  is justified.
- Scale benefits, mix, pricing, raw material costs, labor, R&D, SG&A, and
  utilization are reflected.
- Margin expansion is not assumed without operating leverage or cost evidence.

Investment and working capital:

- CapEx matches growth, capacity, maintenance needs, and asset intensity.
- D&A/revenue is consistent with asset base, CapEx, depreciation policy, and
  peer ranges.
- NWC assumptions match receivables, inventory, payables, channel terms,
  customer concentration, and inventory cycle.
- Growth does not create unrealistic free cash flow by starving investment or
  working capital.

WACC and terminal value:

- WACC uses market-value capital structure where possible.
- Risk-free rate, beta, equity risk premium, cost of debt, and tax shield are
  documented.
- WACC level matches business, country, liquidity, leverage, cyclicality, and
  forecast risk.
- Terminal growth is below WACC.
- Terminal growth is consistent with industry maturity and long-run nominal
  growth.
- Terminal value share of enterprise value is calculated and explained if high.

Cross-method logic:

- DCF result is checked against trading comps.
- Precedent transactions are included or explicitly excluded.
- Historical multiple conflicts are explained.
- Market-implied expectations are compared with Base case assumptions.
- Price target has a valuation range and method weights.

Falsifiability:

- Key assumptions have concrete confirm/refute indicators.
- Next catalysts or reporting items are linked to value drivers.
- `[UNSOURCED]` assumptions are visible and do not hide major valuation risk.

## Output: `assumption_audit.md`

Write a concise but complete audit report with these sections:

```markdown
## 1. Audit Verdict
## 2. Blocking Issues
## 3. Required Revisions
## 4. Assumption-by-Assumption Review
## 5. Scenario Stress Test
## 6. Cross-Method Consistency Checks
## 7. Falsifiable Indicators
## 8. Residual Risks
## 9. Audit Trail
```

Verdict values:

- `Pass`: assumptions can proceed to model execution.
- `Pass with Warnings`: proceed, but warnings must be carried into
  `valuation_analysis.md` and `valuation_state.json`.
- `Revise Before Execution`: revise `assumption_pack.md` and rerun the audit.
- `Do Not Proceed`: evidence is too weak or Task 1/2 prerequisites are not
  sufficient.

For each finding include:

- `Severity`: Blocking, Warning, or Note.
- `Assumption`: the exact assumption being challenged.
- `Issue`: what is weak or inconsistent.
- `Evidence`: source or comparison supporting the challenge.
- `Required action`: revise, source, explain, sensitize, or disclose.

## Revision Loop

If the verdict is `Revise Before Execution`:

1. Revise `assumption_pack.md`.
2. Record the change in `## 9. Audit Trail`.
3. Rerun this audit.
4. Continue only after the verdict is `Pass` or `Pass with Warnings`.

If the verdict is `Do Not Proceed`, stop Task 3 and report the blocker to the
parent agent. Do not create placeholder `dcf_model.xlsx`, `comps.xlsx`, or price
target artifacts.
