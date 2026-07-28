#!/usr/bin/env python3
"""Validate a WeChat rich-text copy boundary and any data tables it contains."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
FORBIDDEN_TAGS = {"canvas", "iframe", "script", "style", "svg", "video"}
FORBIDDEN_STYLE_PATTERNS = {
    "flex/grid layout": re.compile(r"(?:^|;)\s*display\s*:\s*(?:inline-)?(?:flex|grid)\b", re.I),
    "positioned layout": re.compile(r"(?:^|;)\s*position\s*:\s*(?:absolute|fixed|sticky)\b", re.I),
    "gradient": re.compile(r"(?:linear|radial|conic)-gradient\s*\(", re.I),
    "background image": re.compile(r"background(?:-image)?\s*:[^;]*url\s*\(", re.I),
    "CSS variable": re.compile(r"(?:var\s*\(|--[\w-]+\s*:)", re.I),
    "layout transform": re.compile(r"(?:^|;)\s*transform\s*:", re.I),
    # A percentage cap other than 100% does not survive WeChat's paste rewrite,
    # so it cannot be relied on to hold a fixed px width in check.
    "fractional percentage max-width": re.compile(
        r"(?:^|;)\s*max-width\s*:\s*(?!100(?:\.0+)?\s*%)\d+(?:\.\d+)?\s*%", re.I
    ),
}
# Widest inline px width an image may carry: it must still fit a 320px phone
# (288px of body width) without being clipped.
MAX_INLINE_IMAGE_PX = 300
INLINE_PX_WIDTH_RE = re.compile(
    r"(?:^|;)\s*width\s*:\s*([\d.]+)px(?:\s*!important)?\s*(?:;|$)", re.I
)
INLINE_PX_MAX_WIDTH_RE = re.compile(
    r"(?:^|;)\s*max-width\s*:\s*([\d.]+)px(?:\s*!important)?\s*(?:;|$)", re.I
)
REQUIRED_COMPLIANCE_TEXTS = {
    "disclaimer": (
        "免责声明：本文内容均基于客观市场行情交易数据产生，"
        "数据来源于证券交易所官网公开数据，文中内容不构成任何投资建议，"
        "市场有风险，投资需谨慎。"
    ),
    "risk_warning": (
        "风险提示：融资融券交易有风险，投资者在参与融资融券交易前请务必阅读、"
        "了解和掌握有关法律法规和交易所、证券登记结算机构业务规则等相关规则和"
        "《风险揭示书》。"
    ),
}


def _attrs(items: list[tuple[str, str | None]]) -> dict[str, str]:
    return {name.lower(): value or "" for name, value in items}


class CopyBoundaryParser(HTMLParser):
    """Collect tags only from inside #wechat-richtext."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found_target = False
        self.target_depth = 0
        self.nodes: list[tuple[str, dict[str, str]]] = []
        self.tables: list[dict[str, object]] = []
        self.table_stack: list[int] = []
        self.text_parts: list[str] = []

    @property
    def inside_target(self) -> bool:
        return self.target_depth > 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        attr_map = _attrs(attrs)
        if not self.inside_target and attr_map.get("id") == "wechat-richtext":
            self.found_target = True
            self.target_depth = 1
            return
        if not self.inside_target:
            return

        self.nodes.append((tag, attr_map))
        if tag == "table":
            self.tables.append({"attrs": attr_map, "headers": [], "cells": []})
            self.table_stack.append(len(self.tables) - 1)
        elif tag in {"th", "td"} and self.table_stack:
            key = "headers" if tag == "th" else "cells"
            table = self.tables[self.table_stack[-1]]
            table[key].append(attr_map)  # type: ignore[index, union-attr]

        if tag not in VOID_TAGS:
            self.target_depth += 1

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS and self.inside_target:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.inside_target:
            return
        tag = tag.lower()
        if tag == "table" and self.table_stack:
            self.table_stack.pop()
        self.target_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.inside_target:
            self.text_parts.append(data)


def _has_css(style: str, property_name: str, expected: str) -> bool:
    pattern = rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*{expected}(?:\s*!important)?\s*(?:;|$)"
    return bool(re.search(pattern, style, re.I))


def validate(path: Path) -> dict[str, object]:
    html = path.read_text(encoding="utf-8")
    parser = CopyBoundaryParser()
    parser.feed(html)

    errors: list[str] = []
    warnings: list[str] = []

    if not parser.found_target:
        errors.append('missing element with id="wechat-richtext"')
    if not re.search(r"id\s*=\s*['\"]copy-richtext['\"]", html, re.I):
        errors.append('missing copy button with id="copy-richtext"')
    for token in ("ClipboardItem", "'text/html'", "'text/plain'", "content.innerHTML"):
        if token not in html:
            errors.append(f"copy script is missing {token}")
    if not re.search(r"#wechat-richtext\s*\{[^}]*max-width\s*:\s*(?:[1-2]?\d\d|3[0-6]\d|37[0-5])px", html, re.I | re.S):
        errors.append(
            "#wechat-richtext preview max-width must be 375px or less: the preview "
            "width has to be the phone width, not the 677px PC editor width"
        )

    images: list[dict[str, str]] = []
    required_brand_assets = {"logo": False, "qrcode": False}
    for tag, attrs in parser.nodes:
        if tag in FORBIDDEN_TAGS:
            errors.append(f"forbidden <{tag}> inside copied fragment")
        if "class" in attrs:
            errors.append(f"class attribute is not allowed inside copied fragment (<{tag}>)")
        if "id" in attrs:
            errors.append(f"nested id is not allowed inside copied fragment (<{tag}>)")

        style = attrs.get("style", "")
        for label, pattern in FORBIDDEN_STYLE_PATTERNS.items():
            if pattern.search(style):
                errors.append(f"forbidden {label} inside copied fragment (<{tag}>)")

        if tag == "img":
            images.append(attrs)
            src = attrs.get("src", "")
            if not src.lower().startswith("data:image/"):
                errors.append("every copied image must use an embedded data:image URI")
            brand_role = attrs.get("data-brand-asset", "").lower()
            if brand_role in required_brand_assets and src.lower().startswith("data:image/"):
                required_brand_assets[brand_role] = True
            width = attrs.get("width", "")
            if not width.isdigit() or int(width) <= 0:
                errors.append("every copied image must have a positive integer width attribute")
            if not _has_css(style, "width", r"(?:\d+(?:\.\d+)?px|100%)"):
                errors.append("every copied image must have an inline px or 100% width")
            if not _has_css(style, "height", "auto"):
                errors.append("every copied image must have inline height:auto")

            px_width = INLINE_PX_WIDTH_RE.search(style)
            if px_width and float(px_width.group(1)) > MAX_INLINE_IMAGE_PX:
                errors.append(
                    f"image with a fixed {px_width.group(1)}px width is wider than the "
                    f"{MAX_INLINE_IMAGE_PX}px a phone can show; use "
                    "width:100%!important with a max-width:<px>!important cap instead"
                )
            if _has_css(style, "width", "100%") and not INLINE_PX_MAX_WIDTH_RE.search(style):
                errors.append(
                    "image with width:100% must also set an inline max-width in px so it "
                    "never renders larger than the size it was designed for"
                )

    data_tables = [table for table in parser.tables if table["headers"]]
    for index, table in enumerate(data_tables, start=1):
        table_attrs = table["attrs"]
        assert isinstance(table_attrs, dict)
        table_style = table_attrs.get("style", "")
        for prop, expected in (
            ("width", "100%"),
            ("border-collapse", "collapse"),
            ("border-spacing", "0"),
            ("table-layout", "auto"),
        ):
            if not _has_css(table_style, prop, re.escape(expected)):
                errors.append(f"data table {index} must set inline {prop}:{expected}")

        headers = table["headers"]
        cells = table["cells"]
        assert isinstance(headers, list) and isinstance(cells, list)
        for kind, expected_size, items in (
            ("th", "11px", headers),
            ("td", "12px", cells),
        ):
            # One message per broken rule rather than one per cell: a five-row
            # table would otherwise bury every other error under 25 repeats.
            failures: dict[str, list[int]] = {}
            for cell_index, attrs in enumerate(items, start=1):
                style = attrs.get("style", "")
                if attrs.get("align", "").lower() != "center":
                    failures.setdefault("needs align=center", []).append(cell_index)
                if attrs.get("valign", "").lower() != "middle":
                    failures.setdefault("needs valign=middle", []).append(cell_index)
                if not _has_css(style, "text-align", "center"):
                    failures.setdefault("needs text-align:center", []).append(cell_index)
                if not _has_css(style, "vertical-align", "middle"):
                    failures.setdefault("needs vertical-align:middle", []).append(cell_index)
                if not _has_css(style, "font-size", re.escape(expected_size)):
                    failures.setdefault(f"must use font-size:{expected_size}", []).append(cell_index)
            for rule, cell_indexes in failures.items():
                errors.append(
                    f"data table {index} {kind} {rule} "
                    f"({len(cell_indexes)} cell(s), first at {kind} {cell_indexes[0]})"
                )

    for brand_role, present in required_brand_assets.items():
        if not present:
            errors.append(
                f'required embedded brand image is missing: data-brand-asset="{brand_role}"'
            )

    copied_text = re.sub(r"\s+", "", "".join(parser.text_parts))
    required_compliance = {}
    for label, required_text in REQUIRED_COMPLIANCE_TEXTS.items():
        present = re.sub(r"\s+", "", required_text) in copied_text
        required_compliance[label] = present
        if not present:
            errors.append(f"missing exact required compliance text: {label}")

    # Preserve order while suppressing repeated errors from large tables.
    errors = list(dict.fromkeys(errors))
    return {
        "path": str(path.resolve()),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "copied_tag_count": len(parser.nodes),
        "embedded_image_count": len(images),
        "required_brand_assets": required_brand_assets,
        "required_compliance_texts": required_compliance,
        "data_table_count": len(data_tables),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a margin-trading WeChat rich-text companion HTML."
    )
    parser.add_argument("html", type=Path, help="Path to richtext/<seq>.html")
    args = parser.parse_args()

    if not args.html.is_file():
        print(json.dumps({"valid": False, "errors": [f"file not found: {args.html}"]}, ensure_ascii=False))
        return 2

    result = validate(args.html)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
