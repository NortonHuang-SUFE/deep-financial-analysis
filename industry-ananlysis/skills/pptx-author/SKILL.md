---
name: pptx-author
description: "Create PPTX slide decks through the local Swiss HTML renderer. Use when the user asks for slides, a PowerPoint deck, a PPT/PPTX artifact, or an HTML source deck; always call build_pptx with the structured Swiss schema."
tags:
  - presentation
  - powerpoint
  - html-deck
  - swiss-style
allowed-tools: read_file build_pptx
---

# pptx-author

Always call `build_pptx` for slide decks. Do not hand-build PPTX files and do not manually run render scripts unless debugging a failed tool run.

The public tool name is still `build_pptx`, but its implementation is the Swiss pipeline: structured JSON in, `./out/<timestamp>/ppt/index.html`, rendered slide PNGs, and `./out/<timestamp>/ppt/<name>.pptx` out.

## Operating Rules

- Do not run guizang's question intake flow.
- Assume the user already has content; read the provided notes, report, outline, or prompt and organize it into slides.
- Ask only for missing required inputs such as an absent source file path.
- Always choose Swiss International Style B.
- Use IKB / Klein blue as the default single accent.
- Do not generate new AI images by default. BabelArk GPT image generation is intentionally not wired in this version.
- Keep the guizang assets and references available, but do not credit them inside generated decks unless the user asks.

## Tool Contract

Call:

```python
build_pptx(
    slides_json=json.dumps(deck, ensure_ascii=False),
    output_name="deck-name-without-extension",
    output_dir="./out"
)
```

If the current task already created a timestamped task directory, pass that directory as `output_dir`; the tool will still write artifacts under its `ppt/` child. The deprecated `template_path` argument may be omitted.

The tool returns a concise artifact summary with the PPTX path first. Final delivery must report the `.pptx` first.

## JSON Schema

Use this deck shape:

```json
{
  "title": "中国半导体行业研究报告",
  "subtitle": "国产替代 + AI 算力 + 周期上行",
  "meta": "2026.05 · Semiconductor China",
  "slides": [
    {
      "layout": "cover",
      "title": "中国半导体\n战略窗口",
      "kicker": "SECTOR FIELD NOTE",
      "subtitle": "国产替代 + AI 算力 + 周期上行"
    },
    {
      "layout": "kpi",
      "title": "国产替代仍是最大变量",
      "kicker": "MARKET SCALE · 01",
      "metrics": [
        {"value": "4,842.8亿块", "label": "2025E 中国集成电路产量"}
      ],
      "bullets": ["AI芯片、存储复苏、汽车电子推动扩张"],
      "footnote": "Source: 国家统计局/EDB"
    }
  ]
}
```

Supported `layout` values:

- `cover`: title, kicker, subtitle, meta.
- `kpi`: metrics, bullets, callout, footnote.
- `cards`: cards or items, each with title/body/tag/accent.
- `comparison`: left/right groups or left_items/right_items.
- `bar_chart`: bars or data, optional highlight, callout_value, callout_text.
- `table`: headers and rows, or table.headers/table.rows.
- `closing`: title, subtitle, takeaways or items.

These map internally to registered Swiss layouts such as `SWISS-COVER-ASCII`, `S02`, `S15`, `S08`, `S07`, `S21`, and `SWISS-CLOSING-ASCII`. Do not invent layout ids in `slides_json`.

## Slide Writing

- One idea per slide.
- Use insight titles, not labels.
- Prefer 6-10 slides for a compact research report unless the user asks for a longer deck.
- Start with `cover` and end with `closing` when the structure supports it.
- Convert dense prose into metrics, cards, comparisons, charts, or tables.
- Keep each field short enough for a 16:9 slide; trim before calling the tool.

## Swiss Rules

- Treat Swiss as a locked layout system, not a visual mood.
- Use one accent color per deck.
- Use left/top aligned titles except statement or split layouts handled by the tool.
- Use sans-serif typography only.
- Keep straight edges, pure fills, hairlines, and grid alignment.
- Avoid shadows, gradients, glass effects, rounded decorative cards, and mixed accents.
- Keep body text projection-readable and leave the bottom safe area clear.
- Visible text belongs in HTML, not SVG.

## Images

- Do not generate new images unless the user explicitly asks in a future task.
- If the user provides screenshots or images, preserve the real content.
- Use `references/screenshot-framing.md` and `assets/screenshot-backgrounds/` for programmatic screenshot fitting when needed.
- Local images must be copied under the deck's `ppt/images/` directory and referenced by relative paths when a future image-enabled layout supports them.
- `references/image-prompts.md` is retained only for future image-generation work.

## References

Read these only when needed:

- `references/swiss-layout-lock.md` for hard Swiss constraints.
- `references/layouts-swiss.md` for layout intent.
- `references/themes-swiss.md` for Swiss accent definitions.
- `references/screenshot-framing.md` for screenshots.
- `references/swiss-map-component.md` for maps and location pages.
- `references/checklist.md` before deeper manual QA.

## Validation

The tool writes and renders the deck. For debugging or manual QA, check:

```bash
node skills/pptx-author/scripts/validate-swiss-deck.mjs ./out/<timestamp>/ppt/index.html
```

Expected artifacts:

- `./out/<timestamp>/ppt/index.html`
- `./out/<timestamp>/ppt/rendered-slides/01.png`, `02.png`, etc.
- `./out/<timestamp>/ppt/<name>.pptx`
- `./out/<timestamp>/ppt/manifest.json`
