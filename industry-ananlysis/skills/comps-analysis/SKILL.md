---
name: comps-analysis
description: |
  Build institutional-grade comparable company analyses with operating metrics, valuation multiples, and statistical benchmarking in Excel/spreadsheet format.

  Perfect for:
  - Public company valuation (M&A, investment analysis)
  - Benchmarking performance vs. industry peers
  - Pricing IPOs or funding rounds
  - Identifying valuation outliers (over/under-valued)
  - Supporting investment committee presentations
  - Creating sector overview reports

  Not ideal for:
  - Private companies without comparable public peers
  - Highly diversified conglomerates
  - Distressed/bankrupt companies
  - Pre-revenue startups
  - Companies with unique business models
tags:
  - financial-modeling
  - valuation
  - excel
allowed-tools: web_search read_file write_file build_comps_excel
---

# Comparable Company Analysis

## CRITICAL: Data Source Priority (READ FIRST)

**ALWAYS follow this data source hierarchy:**

1. **FIRST: Check for available financial data MCPs** — If any financial data MCPs are configured in your environment, use them exclusively for financial and trading information
2. **DO NOT use web search** if the above MCP data sources are available
3. **ONLY if MCPs are unavailable:** Then use web search to find SEC EDGAR filings, earnings releases, or institutional sources
4. **NEVER use web search as a primary data source** — it lacks the accuracy, audit trails, and reliability required for institutional-grade analysis

---

## Core Philosophy
**"Build the right structure first, then let the data tell the story."**

Start with headers that force strategic thinking about what matters, input clean data, build transparent formulas, and let statistics emerge automatically.

---

## CRITICAL: Formulas Over Hardcodes + Step-by-Step Build

**When generating the Excel file via `build_comps_excel` tool:**
- Every derived value (margin, multiple, statistic) MUST be provided as an Excel formula — never a pre-computed number
- The only hardcoded values should be raw input data (revenue, EBITDA, share price, etc.) — and every hardcoded input needs a source citation in the cell comment
- Why: the model must update automatically when an input changes

**Verify step-by-step with the user:**
- After gathering raw data → confirm sources/periods before building
- After building → show the user the calculated margins and sanity-check
- Do NOT build the entire sheet end-to-end without checkpoints

---

## Document Structure

### Header Block (Rows 1-3)
```
Row 1: [ANALYSIS TITLE] - COMPARABLE COMPANY ANALYSIS
Row 2: [List of Companies with Tickers] • [Company 1 (TICK1)] • [Company 2 (TICK2)]
Row 3: As of [Period] | All figures in [USD Millions/Billions] except per-share amounts
```

### Visual Conventions (defaults — user preferences always override)

- **Font**: Times New Roman, 11pt data cells, 12pt headers
- **Section headers**: Dark blue background (#1F4E79), white bold text
- **Column headers**: Light blue background (#D9E1F2), black bold text
- **Data rows**: White background
- **Statistics rows**: Light gray background (#F2F2F2)
- **Decimal precision**: Percentages 1 decimal (12.3%), multiples 1 decimal (13.5x), dollars no decimals with thousands separator (69,632)
- **Alignment**: Center for metrics, left for labels

---

## Section 1: Operating Statistics & Financial Metrics

### Core Columns
1. Company
2. Revenue (LTM or annual)
3. Revenue Growth (YoY %)
4. Gross Profit
5. Gross Margin = Gross Profit / Revenue
6. EBITDA
7. EBITDA Margin = EBITDA / Revenue

### Optional Additions
- Free Cash Flow, FCF Margin
- Net Income
- Rule of 40 (SaaS: Growth % + FCF Margin %)
- Industry-specific: ARR/NRR (SaaS), ROE/ROA (financials), etc.

### Statistics Block (after company data, one blank row separator)
```
Maximum:        =MAX(range)
75th Percentile: =QUARTILE(range,3)
Median:         =MEDIAN(range)
25th Percentile: =QUARTILE(range,1)
Minimum:        =MIN(range)
```

Only add statistics for comparable metrics (ratios, margins, growth rates) — NOT absolute size metrics (revenue, EBITDA in dollars).

---

## Section 2: Valuation Multiples

### Core Columns
1. Company
2. Market Cap
3. Enterprise Value
4. EV/Revenue
5. EV/EBITDA
6. P/E Ratio

### Formula Examples
```
EV/Revenue  = Enterprise Value / LTM Revenue  (references operating section)
EV/EBITDA   = Enterprise Value / LTM EBITDA   (references operating section)
P/E Ratio   = Market Cap / Net Income
```

**Cross-Reference Rule:** Valuation multiples MUST reference the operating metrics section. Never input the same raw data twice.

Same statistics structure as Section 1.

---

## Section 3: Notes & Methodology

Required:
- **Data sources** — Where, what period, how verified? (Prioritize MCP sources)
- **Key definitions** — EBITDA method, FCF formula, special metrics, time period definitions
- **Valuation methodology** — EV calculation, any adjustments

---

## Section 4: Industry-Specific Metric Selection

**"Which company is undervalued?"** → Focus on EV/Revenue, EV/EBITDA, P/E

**"Which company is most efficient?"** → Focus on Gross Margin, EBITDA Margin, FCF Margin

**"Which is the best cash generator?"** → Focus on FCF, FCF Margin, FCF Conversion

**The "5-10 Rule":** 5 operating + 5 valuation = 10 total columns (sweet spot)

**Industry-Specific:**
- SaaS: ARR, Net Dollar Retention, Rule of 40, gross margin >70%
- Manufacturing: EBITDA Margin, Asset Turnover, CapEx/Revenue, ROA
- Financial Services: ROE, ROA, Efficiency Ratio, P/E (NOT EBITDA)
- Retail/E-commerce: Revenue Growth, Gross Margin, Inventory Turnover

---

## Workflow

### How to build the comps

1. Gather all raw data using available MCP tools (capiq, factset) or web search as fallback
2. Structure the data as JSON: list of companies with revenue, ebitda, market_cap, enterprise_value, growth, etc.
3. Call the `build_comps_excel` tool with the structured data — it generates the .xlsx file
4. Ensure the Excel file is written into the task output directory for this run. If an upstream orchestrator supplied an `output_dir`, pass that exact directory to `build_comps_excel`; do not create another top-level `./out/<timestamp>` source.
5. Report the output path and key findings to the user

### Sanity Checks
- Margin test: Gross margin > EBITDA margin > Net margin (always true by definition)
- EV/Revenue: typically 0.5-20x; EV/EBITDA: 8-25x; P/E: 10-50x
- Higher growth → higher multiples
- Check for #DIV/0! or #REF! errors

---

## Output Checklist

- [ ] All companies are truly comparable
- [ ] Data from consistent time periods
- [ ] Units clearly labeled (millions/billions)
- [ ] Formulas reference cells, not hardcoded values
- [ ] All hard-coded inputs have source citations
- [ ] Statistics include Max, 75th, Median, 25th, Min
- [ ] Notes section documents sources and methodology
- [ ] Date stamp is current
