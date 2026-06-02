---
name: comps-analysis
description: Build comparable company analysis inputs and call build_comps_excel.
allowed-tools: build_comps_excel
---

# Comparable Company Analysis

Build a clean peer set before DCF assumptions are finalized.

- Use 4-8 companies with comparable business model, geography, size, and listing context.
- Include source strings for every raw input.
- Do not pass zero, blank, or placeholder values for missing company names, market cap, enterprise value, revenue, EBITDA, or net income. If enterprise value is unavailable, derive it from sourced market cap plus debt minus cash, or gather another sourced EV figure before calling `build_comps_excel`.
- Do not compute multiples manually for the workbook; `build_comps_excel` writes formulas.
- Capture median EV/EBITDA, EV/Revenue, revenue growth, and EBITDA margin as DCF cross-checks.
