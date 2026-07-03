---
name: eng-runbook
zh_name: "工程 Runbook"
en_name: "Engineering Runbook"
emoji: "📕"
description: "服务概述 + alerts 表 + dashboards + 操作命令 + on-call + 事故清单"
category: doc
scenario: engineering
aspect_hint: "长页面"
tags: ["runbook", "ops", "oncall", "sre"]
---

# Engineering Runbook
【意图】工程 oncall 用的可拷贝命令的 runbook 单页。
【布局】
- Service overview (拓扑 + 依赖)
- Alerts table (severity / threshold / runbook link)
- Dashboards links 卡片
- Common procedures (mono 代码块, 一键复制)
- On-call rotation (本周 + 下周)
- Incident response checklist

## Assets

- Example HTML: `assets/example.html`
- After reading this `SKILL.md`, inspect `assets/example.html` in bounded slices before writing HTML. Treat it as the closest visual skeleton for layout rhythm, typography scale, spacing, palette, component structure, and export-ready patterns.
