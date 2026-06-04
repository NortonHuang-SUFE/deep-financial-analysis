---
name: assumption-audit
description: Adversarially audit DCF and valuation assumptions against evidence, logic, and cross-validation benchmarks.
---

# Assumption Audit

Use this skill to run a red-team review of all Bear/Base/Bull DCF assumptions before model execution. The goal is not to produce assumptions — that is the job of `dcf-assumption-generation` — but to challenge each assumption with the question: is there evidence, logic, and verifiability behind this number?

An assumption that passes this audit has three properties:

1. It is grounded in evidence (historical data, peer data, management guidance, or industry data).
2. It is internally consistent (margin improvements are explained by operating leverage or mix, not just optimism).
3. It is falsifiable (there is a specific observable outcome that would prove the assumption wrong).

## The 11-Item Assumption Audit Checklist

Work through each item in order. For each item, document: the assumption value, the supporting evidence, any conflicts with evidence, and a pass / warn / fail verdict.

---

### 1. Revenue Assumptions — Segment-Level Decomposition

**Audit question**: Is revenue growth derived from a product/region/customer/price/volume build, or is it a top-down CAGR applied mechanically?

- Confirm that revenue in the assumption pack is decomposable into at least two of: volume, price, mix, segment.
- Check whether segment-level growth rates are consistent with iFind or disclosed data.
- If a segment has no supporting evidence, flag `[UNSOURCED]`.
- Verify that Base revenue growth is neither the simple average of Bear and Bull, nor the consensus estimate accepted without scrutiny.
- Acceptable evidence: company segment disclosures, iFind segment data, industry volume reports, management guidance with historical accuracy assessment.

**Fail condition**: Revenue assumption is a single blended CAGR with no decomposition and no evidence.

---

### 2. Base Case — Operational Plausibility

**Audit question**: Does the Base case reflect a credible, verifiable operating path — not just the midpoint between bear and bull?

- Identify the key operational milestones implied by Base: production ramp, utilization rate, headcount, product launches.
- Ask: has the company demonstrated the ability to execute this path before?
- Cross-check Base revenue growth against: (a) historical 3-year average growth, (b) management guidance, (c) consensus if available.
- If Base deviates significantly from all three benchmarks, require explicit written justification in the assumption pack.

**Fail condition**: Base case cannot be connected to any observable operational milestone or external benchmark.

---

### 3. Bear Case — Stress Severity

**Audit question**: Is the Bear case a genuine stress scenario, or a cosmetically lower version of Base?

- Compute the Bear-to-Base revenue gap. If the gap is less than 5 percentage points on a cumulative basis over the forecast period, flag as insufficiently stressed.
- Verify that Bear case reflects at least one real-world risk mechanism from the `risk_drivers` in `business_driver_map.json`.
- Bear case should imply a plausible but adverse outcome: demand contraction, pricing pressure, market share loss, cost inflation, or regulatory impact.
- Check whether Bear margins are consistent with a revenue decline scenario (fixed cost deleveraging, not just proportional scaling).

**Fail condition**: Bear revenue is within 3% of Base with no identified stress mechanism.

---

### 4. Bull Case — Evidence Requirement

**Audit question**: Does the Bull case have capacity, demand, pricing, or share evidence — or is it speculative upside?

- Identify the specific driver(s) behind Bull case outperformance: new capacity coming online, a new product cycle, market share gain, ASP recovery, or policy tailwind.
- Require at least one piece of concrete evidence from `business_driver_map.json` catalyst or revenue drivers.
- Check whether Bull revenue or margin assumptions require the company to exceed its historical best performance. If so, require explicit justification.

**Fail condition**: Bull case shows higher revenue and margins with no identified catalyst or evidence linkage.

---

### 5. EBIT Margin — Consistency with History, Peers, and Scale Effects

**Audit question**: Are margin assumptions consistent with (a) the company's historical margin trajectory, (b) peer margins, and (c) operating leverage from revenue growth?

- Pull the company's last 5 years of EBIT margin from `financial_facts.json`. Check whether the assumed margin path is a continuation, an improvement, or a recovery — and whether each is justified.
- Pull the peer margin range from comps data. If the company's assumed Base margin is above the peer 75th percentile, require an explicit moat or scale argument.
- Check whether margin improvement in Base/Bull correlates with revenue scale (fixed-cost leverage) or requires cost reductions that are not yet contracted.
- Flag if EBIT margin is projected to expand while revenue is declining (Bear) without a clear mix or cost restructuring explanation.

**Fail condition**: Margin assumptions are disconnected from revenue trajectory and have no peer or historical anchor.

---

### 6. CapEx — Alignment with Growth, Capacity, and Maintenance Needs

**Audit question**: Is CapEx sized appropriately for the growth assumed, and does it distinguish maintenance from growth investment?

- Verify that Base/Bull CapEx is consistent with the capacity expansion implied by revenue growth assumptions. A company projecting 20% revenue growth but flat CapEx requires explanation.
- Check that Bear CapEx is not lower than maintenance CapEx — maintenance investment cannot be deferred indefinitely without impairing the asset base.
- Cross-check CapEx/revenue ratio against the company's own historical range (from `financial_facts.json`) and peer range.
- If the company has publicly disclosed a capital expenditure plan or investment program, verify that assumptions are consistent with disclosed guidance.

**Fail condition**: CapEx/revenue in Bull is below the historical minimum with no explanation, or Bear CapEx is below estimated maintenance level.

---

### 7. NWC — Business Model and Commercial Cycle Consistency

**Audit question**: Are NWC assumptions consistent with the company's commercial model, payment terms, and inventory cycle?

- Extract receivables days, payables days, and inventory days from `financial_facts.json`. Verify that NWC/revenue assumptions imply DSO, DIO, DPO within a plausible range of historical norms.
- Check for consistency with the business model: a contract manufacturer with advance payments should show negative NWC; a capital goods seller with long payment terms should show high receivables.
- Flag if NWC is assumed to improve materially (cash conversion accelerates) without a commercial or operational justification.
- In Bear case, check whether NWC could worsen (customers stretch payables, inventory builds as demand falls).

**Fail condition**: NWC assumptions contradict the company's known payment terms or historical cycle without explanation.

---

### 8. WACC — Market Value Capital Structure

**Audit question**: Is WACC computed using market value weights for debt and equity, not book values?

- Confirm that equity weight uses market cap (current share price × shares outstanding), not book equity.
- Confirm that debt weight uses market value of debt. For investment-grade issuers with liquid bonds, check whether bond prices differ materially from par. For bank debt, par approximation is acceptable with a note.
- Verify cost of equity derivation: risk-free rate, equity risk premium, and beta source.
  - Risk-free rate should be the long-term government bond yield in the reporting currency.
  - ERP should reflect country-specific or market-specific premium (not a US-only ERP for an A-share company).
  - Beta should be observed or estimated from comps, not assumed at 1.0 without justification.
- Verify cost of debt: use yield to maturity on outstanding bonds if available; otherwise use the company's marginal borrowing rate, not coupon on legacy debt.
- Verify tax rate used in after-tax cost of debt is consistent with the effective tax rate used in the model.

**Fail condition**: WACC uses book value weights, or cost of equity uses US ERP for a non-US company without adjustment.

---

### 9. Terminal Growth Rate — WACC Spread and Industry Maturity

**Audit question**: Is terminal growth rate below WACC, and is it consistent with the long-run growth outlook for this industry?

- Verify mathematically: terminal growth < WACC. If not, the Gordon Growth Model produces a negative or infinite value. This is a hard fail.
- Assess whether terminal growth is consistent with long-run nominal GDP growth in the primary market, adjusted for industry maturity:
  - Mature, commoditized industries: terminal growth should be at or below nominal GDP.
  - Structural growth industries: may justify modestly above nominal GDP for a limited period, but must revert.
- Check that terminal growth is not set equal to near-term projected growth rates — the terminal period represents steady-state, not continued high growth.

**Fail condition**: Terminal growth >= WACC (mathematical error) or terminal growth exceeds long-run nominal GDP with no justification.

---

### 10. Terminal Value as Percentage of Enterprise Value

**Audit question**: Is terminal value dominance acknowledged and justified?

- Compute terminal value as a percentage of total DCF enterprise value for Base case.
- If terminal value exceeds 75% of EV, flag as a yellow warning and require the following:
  - Explanation of why the explicit forecast period is short (if < 5 years, consider extending).
  - Sensitivity analysis showing how the price target moves with ±0.5% changes in terminal growth and ±1% changes in WACC.
  - Acknowledgment in `assumption_pack.md` that valuation is heavily dependent on terminal assumptions.
- If terminal value exceeds 90% of EV, escalate to a red flag. Consider whether the forecast period is long enough, or whether the business is too early-stage for a DCF to be the primary method.

**Warning threshold**: TV > 75% of EV. **Fail condition**: TV > 90% of EV without sensitivity disclosure.

---

### 11. DCF vs. Comps Reconciliation — Conflict Explanation

**Audit question**: If the DCF value conflicts with trading comps or precedent transactions, is the conflict explained?

- Compare the Base DCF implied multiple (EV/EBITDA, P/E) against the comps range produced in `valuation-reconciliation`.
- If DCF implied multiple is more than 1 standard deviation above the comps median, require an explicit argument for why the intrinsic value exceeds the current market pricing of peers.
- If DCF implied multiple is more than 1 standard deviation below the comps median, require an explanation of why the company deserves a discount (weaker margins, higher leverage, governance discount, or cyclical headwinds).
- Document whether the reconciliation gap is driven by growth, margin, or WACC differences between the DCF assumptions and what the comps multiples imply.

**Fail condition**: DCF and comps diverge by >2 standard deviations with no documented explanation.

---

## Audit Output Format

For each checklist item, produce a block with:

```
### Item N: [Name]
Assumption value: [Bear / Base / Bull values]
Evidence: [what supports this]
Conflicts: [what contradicts this, if anything]
Verdict: PASS | WARN | FAIL
Notes: [any required follow-up or condition for upgrade]
```

## Output

Produce `assumption_audit.md` under `03_valuation/` containing:

1. Audit summary: overall verdict (Clean / Issues Found / Blocked), count of PASS / WARN / FAIL items.
2. All 11 checklist items with individual verdicts.
3. Required actions before model execution: list any FAIL items that must be resolved before proceeding to Step 3.5 (Model Execution).
4. Conditional approvals: list any WARN items with the condition under which they are acceptable.

## Escalation Rule

If any of the following items are FAIL, do not proceed to model execution until resolved:

- Item 1 (Revenue Decomposition)
- Item 8 (WACC Market Value Structure)
- Item 9 (Terminal Growth < WACC)

All other FAIL items require a written justification in `assumption_pack.md` before proceeding.
