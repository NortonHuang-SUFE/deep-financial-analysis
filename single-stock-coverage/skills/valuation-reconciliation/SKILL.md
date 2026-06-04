---
name: valuation-reconciliation
description: Reconciles DCF, trading comps, precedent transactions, historical multiples, and market-implied expectations into a weighted valuation range and machine-readable valuation state.
---

# Valuation Reconciliation

Use this skill after audited assumptions have been executed through the DCF and
comps workbooks. This skill converts model outputs and cross-checks into the
final Task 3 valuation conclusion.

## Inputs

Required:

- `evidence_sufficiency.md`
- `value_driver_map.json`
- `assumption_pack.md`
- `assumption_audit.md`
- `dcf_model.xlsx`
- `comps.xlsx`
- `precedent_transactions.xlsx`, if applicable.
- Task 2 financial facts and integrated model.
- Current price and market data date.
- Historical multiples and market-implied expectation evidence, when available.
- Workbook validation and audit outputs, when available.

## Reconciliation Workflow

1. Extract method outputs.
   - DCF Low/Base/High price per share, EV, equity value, WACC, terminal growth,
     terminal value share, and sensitivity ranges.
   - Trading comps Low/Base/High using selected multiples and peer statistics.
   - Precedent transactions Low/Base/High if relevant.
   - Historical multiple range if the company has useful trading history.
   - Market-implied growth or margin assumptions at current price.

2. Diagnose conflicts.
   - Identify methods that imply materially different values.
   - Explain whether the difference is caused by forecast risk, peer mismatch,
     control premium, cycle timing, accounting differences, capital structure,
     or market sentiment.

3. Assign weights.
   - DCF gets higher weight when Task 1/2 evidence and assumptions are strong.
   - Trading comps gets higher weight when the peer set is clean and current
     market pricing is credible.
   - Precedent transactions gets higher weight when M&A is realistic and
     transactions are relevant.
   - Historical multiples and market-implied checks normally receive 0% primary
     weight unless explicitly used as valuation methods.
   - Primary method weights must total 100%.

4. Build final range.
   - Present Low/Base/High for each method.
   - Calculate weighted Low/Base/High if appropriate.
   - Select a price target within the Base range or explain why a different
     point in the range is more defensible.
   - Calculate upside/downside from current price.

5. Run sanity checks.
   - Historical multiple check.
   - Peer premium/discount check.
   - Market-implied growth check.
   - IRR or implied return check.
   - Market-cap reasonableness check.
   - Terminal value share check.
   - WACC reasonableness check.
   - Scenario severity check.
   - Source and `[UNSOURCED]` check.

6. Update the assumption pack.
   - Fill `## 7. DCF 输出`.
   - Fill `## 8. 估值方法交叉验证`.
   - Ensure `## 1. 估值结论` matches the final conclusion.

## Required `valuation_analysis.md`

Write `valuation_analysis.md` with these sections:

```markdown
## 1. Valuation Conclusion
## 2. Evidence and Assumption Quality
## 3. DCF Analysis
## 4. Trading Comparables
## 5. Precedent Transactions
## 6. Valuation Reconciliation
## 7. Sanity Checks
## 8. Falsifiable Indicators and Follow-Up
## 9. Sources, Gaps, and Audit Warnings
```

Include this mandatory table:

```markdown
| Method | Low | Base | High | Weight | Rationale |
| --- | ---: | ---: | ---: | ---: | --- |
| DCF | | | | | |
| Trading Comps | | | | | |
| Precedent Transactions | | | | | |
| Historical Multiples | | | | | |
| Market-Implied Check | | | | | |
```

Also include:

- Current price and date.
- Valuation date.
- Currency and share-count basis.
- Price target or valuation range.
- Upside/downside.
- Rating or recommendation if the parent workflow requests one.
- Method conflicts and resolution.
- Workbook validation/audit warnings.
- `[UNSOURCED]` items.

## Required `valuation_state.json`

Write machine-readable state with this shape:

```json
{
  "company": "",
  "ticker": "",
  "market": "",
  "currency": "",
  "valuation_date": "",
  "current_price": {
    "value": null,
    "date": "",
    "source": ""
  },
  "price_target": {
    "value": null,
    "horizon": "",
    "currency": "",
    "method": ""
  },
  "valuation_range": {
    "low": null,
    "base": null,
    "high": null
  },
  "rating_or_recommendation": "",
  "method_outputs": {
    "dcf": {},
    "trading_comps": {},
    "precedent_transactions": {},
    "historical_multiples": {},
    "market_implied_check": {}
  },
  "method_weights": {
    "dcf": null,
    "trading_comps": null,
    "precedent_transactions": null,
    "historical_multiples": null,
    "market_implied_check": null
  },
  "key_assumptions": {},
  "scenario_summary": {
    "bear": {},
    "base": {},
    "bull": {}
  },
  "sanity_checks": [],
  "falsifiable_indicators": [],
  "artifact_paths": {
    "evidence_sufficiency": "",
    "value_driver_map": "",
    "assumption_pack": "",
    "assumption_audit": "",
    "dcf_model": "",
    "comps": "",
    "precedent_transactions": "",
    "valuation_analysis": ""
  },
  "source_refs": [],
  "unsourced_items": [],
  "audit_warnings": [],
  "last_updated": ""
}
```

Use `null` only when a value is genuinely unavailable and explain the gap in
`unsourced_items` or `audit_warnings`.

## Quality Bar

- Do not hide a method because it conflicts with the preferred target.
- Do not give primary weight to precedent transactions without M&A relevance.
- Do not let sanity checks be perfunctory; they must have explicit pass/warn
  conclusions.
- Do not finalize a price target if DCF workbook validation has unresolved
  critical errors.
- Do not let the final valuation conclusion disagree with the updated
  `assumption_pack.md`.
