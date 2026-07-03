---
name: email-marketing
zh_name: "营销邮件"
en_name: "Marketing Email"
emoji: "📧"
description: "产品发布邮件, 含 masthead、hero、CTA、规格表, table-fallback"
category: email
scenario: marketing
aspect_hint: "600 邮件宽"
featured: 7
tags: ["email", "newsletter", "mjml"]
---

# 品牌产品发布邮件
【意图】纯 HTML 邮件, 600px 单栏, 兼容邮件客户端。
【布局】
- Masthead (wordmark 居中)
- Hero 图块 (SVG 占位)
- Headline lockup (含 skewed-italic accent)
- Body copy + primary CTA 按钮
- Specifications grid (3 列)
- Footer (社交 + 退订)
【设计细节】
- 使用 `<table role='presentation'>` 做布局兜底
- 颜色用 inline style (不要依赖 class)

## Assets

- Example HTML: `assets/example.html`
- After reading this `SKILL.md`, inspect `assets/example.html` in bounded slices before writing HTML. Treat it as the closest visual skeleton for layout rhythm, typography scale, spacing, palette, component structure, and export-ready patterns.
