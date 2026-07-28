#!/usr/bin/env python3
"""Check a WeChat rich-text fragment at real phone widths.

The PC editor renders the article body at 677px, so a fragment authored and
reviewed there can still break on a phone, where WeChat only gives the body
about `viewport - 32px` and clips overflow instead of scrolling it.

This script loads `#wechat-richtext` at each requested viewport width, wraps it
in a shell that mimics the WeChat mobile article container, and fails on the
symptoms that PC review cannot catch: horizontal clipping, table headers that
wrap or stack vertically, cells that wrap too far, tables squeezed by container
padding, and type below the readable floor.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# WeChat mobile puts 16px of horizontal padding on each side of the article body.
ARTICLE_SIDE_PADDING = 16
DEFAULT_WIDTHS = (375, 320)
# Every element inherits these from the WeChat mobile article stylesheet, and
# `#js_content` itself is `overflow: hidden`, so anything wider is cut off.
WECHAT_MOBILE_SHELL_CSS = (
    "#wechat-richtext * {"
    "max-width:100%!important;"
    "box-sizing:border-box!important;"
    "word-wrap:break-word!important;"
    "}"
)

MAX_TH_LINES = 1
MAX_TD_LINES = 2
MIN_TABLE_WIDTH_RATIO = 0.85
MIN_FONT_SIZE_PX = 11.0
# Ratio of the width the author designed the image for (its `width` attribute)
# to the width a phone actually gives it. Above this, type drawn inside the
# image is too small to read.
MAX_IMAGE_DOWNSCALE = 1.8

CHROMIUM_LAUNCH_ARGS = [
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-sandbox",
]

MEASURE_JS = r"""
(contentWidth) => {
  const root = document.getElementById('wechat-richtext');
  if (!root) return { missing: true };

  root.style.setProperty('width', contentWidth + 'px', 'important');
  root.style.setProperty('max-width', contentWidth + 'px', 'important');
  root.style.setProperty('margin', '0', 'important');
  root.style.setProperty('overflow', 'hidden', 'important');

  const shell = document.createElement('style');
  shell.textContent = SHELL_CSS;
  document.head.appendChild(shell);

  // Count the line boxes the cell's own text occupies. Cell height cannot be
  // used: every cell in a row is stretched to the tallest one, so a one-line
  // rank cell would otherwise report as many lines as its neighbours.
  const linesOf = (el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const tops = [];
    for (const rect of range.getClientRects()) {
      if (rect.width <= 0 || rect.height <= 0) continue;
      if (!tops.some((top) => Math.abs(top - rect.top) < 2)) tops.push(rect.top);
    }
    return tops.length;
  };
  const label = (el) => (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 24);

  const clipped = [];
  const smallType = [];
  root.querySelectorAll('*').forEach((el) => {
    if (el.scrollWidth - el.clientWidth > 1) {
      clipped.push({ tag: el.tagName.toLowerCase(), scrollWidth: el.scrollWidth,
                     clientWidth: el.clientWidth, text: label(el) });
    }
    const ownText = [...el.childNodes]
      .filter((n) => n.nodeType === 3 && n.textContent.trim())
      .length > 0;
    if (ownText) {
      const fs = parseFloat(getComputedStyle(el).fontSize) || 0;
      if (fs > 0 && fs < MIN_FONT) {
        smallType.push({ tag: el.tagName.toLowerCase(), fontSize: fs, text: label(el) });
      }
    }
  });

  const tables = [];
  root.querySelectorAll('table').forEach((table, index) => {
    const parentWidth = table.parentElement
      ? table.parentElement.clientWidth
      : root.clientWidth;
    const width = table.getBoundingClientRect().width;
    const headers = [...table.querySelectorAll('th')].map((th) => ({
      text: label(th), lines: linesOf(th),
      width: Math.round(th.getBoundingClientRect().width),
    }));
    const cells = [...table.querySelectorAll('td')].map((td) => ({
      text: label(td), lines: linesOf(td),
    }));
    tables.push({
      index,
      width: Math.round(width),
      parentWidth: Math.round(parentWidth),
      widthRatio: parentWidth ? width / parentWidth : 1,
      headers,
      maxHeaderLines: headers.length ? Math.max(...headers.map((h) => h.lines)) : 0,
      worstHeader: headers.length
        ? headers.reduce((a, b) => (b.lines > a.lines ? b : a)) : null,
      maxCellLines: cells.length ? Math.max(...cells.map((c) => c.lines)) : 0,
      worstCell: cells.length
        ? cells.reduce((a, b) => (b.lines > a.lines ? b : a)) : null,
    });
  });

  const images = [...root.querySelectorAll('img')].map((img) => {
    const rendered = img.getBoundingClientRect().width;
    // The `width` attribute is the width the author designed the image for, so
    // it — not the raster's pixel width — says how much its type shrank.
    const designed = parseInt(img.getAttribute('width') || '', 10) || img.naturalWidth;
    return {
      role: img.getAttribute('data-brand-asset') || '',
      naturalWidth: img.naturalWidth,
      designedWidth: designed,
      renderedWidth: Math.round(rendered),
      downscale: rendered > 0 ? designed / rendered : 0,
    };
  });

  return {
    missing: false,
    contentWidth,
    rootScrollWidth: root.scrollWidth,
    clipped,
    smallType,
    tables,
    images,
  };
}
"""


def _find_browser() -> str | None:
    """Reuse the renderer's system-browser lookup when it is importable."""
    try:
        package_src = Path(__file__).resolve().parents[3] / "src"
        if str(package_src) not in sys.path:
            sys.path.insert(0, str(package_src))
        from html_image_renderer_agent.render_html import find_browser
    except Exception:
        return None
    try:
        return find_browser()
    except Exception:
        return None


def _measure(page: Any, width: int) -> dict[str, Any]:
    script = (
        MEASURE_JS.replace("SHELL_CSS", json.dumps(WECHAT_MOBILE_SHELL_CSS))
        .replace("MIN_FONT", repr(MIN_FONT_SIZE_PX))
    )
    return page.evaluate(script, width - 2 * ARTICLE_SIDE_PADDING)


def check(path: Path, widths: tuple[int, ...] = DEFAULT_WIDTHS) -> dict[str, Any]:
    path = path.expanduser().resolve()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "playwright is required for the WeChat mobile check. Install project "
            "dependencies, then run `python -m playwright install chromium`."
        ) from exc

    errors: list[str] = []
    warnings: list[str] = []
    per_width: dict[str, Any] = {}

    launch_kwargs: dict[str, Any] = {"headless": True, "args": CHROMIUM_LAUNCH_ARGS}
    browser_path = _find_browser()
    if browser_path:
        launch_kwargs["executable_path"] = browser_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            for width in widths:
                page = browser.new_page(viewport={"width": width, "height": 900})
                try:
                    page.goto(path.as_uri(), wait_until="domcontentloaded", timeout=60000)
                    page.evaluate(
                        """async () => {
                          if (document.fonts && document.fonts.ready) await document.fonts.ready;
                          await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
                        }"""
                    )
                    result = _measure(page, width)
                finally:
                    page.close()

                if result.get("missing"):
                    errors.append('missing element with id="wechat-richtext"')
                    continue

                tag = f"@{width}px"
                for item in result["clipped"]:
                    errors.append(
                        f"{tag} horizontal clipping: <{item['tag']}> needs "
                        f"{item['scrollWidth']}px but has {item['clientWidth']}px "
                        f"({item['text']!r})"
                    )
                for item in result["smallType"]:
                    errors.append(
                        f"{tag} font-size {item['fontSize']:.0f}px is below the "
                        f"{MIN_FONT_SIZE_PX:.0f}px floor: <{item['tag']}> ({item['text']!r})"
                    )
                for table in result["tables"]:
                    index = table["index"] + 1
                    if table["maxHeaderLines"] > MAX_TH_LINES:
                        worst = table["worstHeader"] or {}
                        errors.append(
                            f"{tag} table {index} header wraps to "
                            f"{table['maxHeaderLines']} lines in {worst.get('width')}px "
                            f"({worst.get('text')!r}) — shorten the header text or move "
                            "units to a caption line"
                        )
                    if table["maxCellLines"] > MAX_TD_LINES:
                        worst = table["worstCell"] or {}
                        errors.append(
                            f"{tag} table {index} cell wraps to "
                            f"{table['maxCellLines']} lines ({worst.get('text')!r}) — "
                            "shorten the value or drop the column"
                        )
                    if table["widthRatio"] < MIN_TABLE_WIDTH_RATIO:
                        errors.append(
                            f"{tag} table {index} is only {table['width']}px inside a "
                            f"{table['parentWidth']}px container "
                            f"({table['widthRatio']:.0%}) — trim container padding"
                        )
                for image in result["images"]:
                    if image["downscale"] > MAX_IMAGE_DOWNSCALE:
                        warnings.append(
                            f"{tag} image {image['role'] or '(unnamed)'} is shown at "
                            f"{image['renderedWidth']}px but was designed for "
                            f"{image['designedWidth']}px ({image['downscale']:.1f}x) — "
                            "text inside it will be hard to read; rasterize it at phone "
                            "width"
                        )

                per_width[str(width)] = {
                    "content_width": result["contentWidth"],
                    "root_scroll_width": result["rootScrollWidth"],
                    "clipped_element_count": len(result["clipped"]),
                    "tables": [
                        {
                            "index": t["index"] + 1,
                            "width": t["width"],
                            "width_ratio": round(t["widthRatio"], 3),
                            "max_header_lines": t["maxHeaderLines"],
                            "max_cell_lines": t["maxCellLines"],
                        }
                        for t in result["tables"]
                    ],
                    "images": [
                        {
                            "role": i["role"],
                            "rendered_width": i["renderedWidth"],
                            "downscale": round(i["downscale"], 2),
                        }
                        for i in result["images"]
                    ],
                }
        finally:
            browser.close()

    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    return {
        "path": str(path.resolve()),
        "valid": not errors,
        "widths": list(widths),
        "errors": errors,
        "warnings": warnings,
        "measurements": per_width,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a margin-trading WeChat rich-text file at phone widths."
    )
    parser.add_argument("html", type=Path, help="Path to richtext/<seq>.html")
    parser.add_argument(
        "--widths",
        default=",".join(str(w) for w in DEFAULT_WIDTHS),
        help="Comma-separated viewport widths to check (default: 375,320).",
    )
    args = parser.parse_args()

    if not args.html.is_file():
        print(
            json.dumps(
                {"valid": False, "errors": [f"file not found: {args.html}"]},
                ensure_ascii=False,
            )
        )
        return 2

    try:
        widths = tuple(int(w) for w in args.widths.split(",") if w.strip())
    except ValueError:
        print(json.dumps({"valid": False, "errors": [f"bad --widths: {args.widths}"]}))
        return 2
    if not widths:
        print(json.dumps({"valid": False, "errors": ["--widths must list at least one width"]}))
        return 2

    result = check(args.html, widths)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
