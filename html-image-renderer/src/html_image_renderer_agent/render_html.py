#!/usr/bin/env python3
"""Render one local HTML element/page to one PNG.

This module is intentionally deterministic and model-free. The
html_image_renderer Deep Agent writes a standalone HTML file, then calls this
script through LocalShellBackend to produce the final PNG artifact.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import Any


DEFAULT_BROWSER_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PROJECT_ROOT / "skills"
REMOTE_RESOURCE_ATTRS = {"src", "href", "poster", "data", "srcset"}
REMOTE_URL_RE = re.compile(r"https?://|//[A-Za-z0-9_.-]+")
REMOTE_CSS_RE = re.compile(r"(@import\s+|url\()\s*['\"]?(https?:)?//", re.IGNORECASE)


class HtmlContractParser(HTMLParser):
    """Collect enough structure to validate the renderer's HTML contract."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.image_root_attrs: list[dict[str, str]] = []
        self.remote_resources: list[str] = []
        self._in_style = False
        self._style_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if attr_map.get("id") == "image-root":
            self.image_root_attrs.append(attr_map)

        for name, value in attr_map.items():
            if name not in REMOTE_RESOURCE_ATTRS or not value:
                continue
            if REMOTE_URL_RE.search(value):
                self.remote_resources.append(f"{tag}[{name}]={value}")

        if tag.lower() == "style":
            self._in_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_chunks.append(data)

    @property
    def style_text(self) -> str:
        return "\n".join(self._style_chunks)


def load_source_texts(source_paths: list[str]) -> dict[str, str]:
    """Read supported text-like source artifact files.

    The agent normally reads artifacts with built-in file tools. Tests use this
    helper to verify the renderer package handles the same artifact path style.
    """
    loaded: dict[str, str] = {}
    allowed = {".md", ".markdown", ".csv", ".tsv", ".json", ".txt"}
    for raw_path in source_paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        if path.suffix.lower() not in allowed:
            raise ValueError(
                f"Unsupported source file type for text loading: {path.suffix} ({path})"
            )
        loaded[str(path)] = path.read_text(encoding="utf-8")
    return loaded


def find_browser(explicit: str | None = None) -> str | None:
    """Return a system browser executable path if one is available."""
    candidates = [explicit or os.getenv("HTML_IMAGE_RENDERER_BROWSER")]
    candidates.extend(DEFAULT_BROWSER_PATHS)
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def validate_html_contract(
    html_path: str | Path,
    *,
    selector: str = "#image-root",
) -> dict[str, Any]:
    """Validate the renderer-specific HTML contract before Playwright runs."""
    if selector != "#image-root":
        return {"selector": selector, "skipped": True}

    html_file = Path(html_path).expanduser().resolve()
    html_text = html_file.read_text(encoding="utf-8")
    parser = HtmlContractParser()
    parser.feed(html_text)

    root_count = len(parser.image_root_attrs)
    if root_count != 1:
        raise ValueError(
            f"Expected exactly one element matching {selector!r}, found {root_count}."
        )

    root_attrs = parser.image_root_attrs[0]
    skill_id = root_attrs.get("data-html-anything-skill", "").strip()
    if not skill_id:
        raise ValueError(
            "#image-root must include data-html-anything-skill with the selected "
            "HTML Anything skill id."
        )
    if not (SKILLS_DIR / skill_id / "SKILL.md").exists():
        raise ValueError(
            "data-html-anything-skill must match a mounted HTML Anything skill: "
            f"{skill_id!r}."
        )

    if parser.remote_resources:
        preview = "; ".join(parser.remote_resources[:3])
        raise ValueError(
            "HTML must be self-contained and cannot reference remote resources: "
            f"{preview}"
        )
    if REMOTE_CSS_RE.search(parser.style_text):
        raise ValueError(
            "HTML must be self-contained and cannot import remote CSS or url() assets."
        )

    return {
        "selector": selector,
        "skill": skill_id,
        "image_root_count": root_count,
    }


def render_html_file(
    html_path: str | Path,
    png_path: str | Path,
    *,
    selector: str = "#image-root",
    width: int = 1080,
    height: int = 1440,
    device_scale_factor: float = 1,
    full_page: bool = False,
    timeout_ms: int = 60000,
) -> dict[str, Any]:
    """Render a local HTML file to exactly one PNG and return metadata."""
    html_file = Path(html_path).expanduser().resolve()
    if not html_file.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")
    contract = validate_html_contract(html_file, selector=selector)

    png_file = Path(png_path).expanduser().resolve()
    png_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required for HTML image rendering. Install project "
            "dependencies, then run `.venv/bin/python -m playwright install chromium`."
        ) from exc

    try:
        with sync_playwright() as p:
            launch_kwargs: dict[str, Any] = {"headless": True}
            browser_path = find_browser()
            if browser_path:
                launch_kwargs["executable_path"] = browser_path

            browser = p.chromium.launch(**launch_kwargs)
            try:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=device_scale_factor,
                )
                page.route("http://*/*", lambda route: route.abort())
                page.route("https://*/*", lambda route: route.abort())
                page.goto(html_file.as_uri(), wait_until="domcontentloaded", timeout=timeout_ms)
                page.evaluate(
                    """async () => {
                      if (document.fonts && document.fonts.ready) await document.fonts.ready;
                      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
                      await new Promise(r => setTimeout(r, 250));
                    }"""
                )

                target = page.locator(selector)
                target_count = target.count()
                if target_count != 1:
                    raise ValueError(
                        f"Expected exactly one element matching {selector!r}, found {target_count}."
                    )
                target.first.screenshot(path=str(png_file), timeout=timeout_ms)
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise RuntimeError(
            "Could not render HTML with Playwright Chromium. If the browser is "
            "missing, run `.venv/bin/python -m playwright install chromium`."
        ) from exc

    pixel_width, pixel_height = png_dimensions(png_file)
    return {
        "html_path": str(html_file),
        "png_path": str(png_file),
        "width": pixel_width,
        "height": pixel_height,
        "selector": selector,
        "html_anything_skill": contract.get("skill"),
    }


def png_dimensions(path: str | Path) -> tuple[int, int]:
    """Read PNG dimensions from the IHDR chunk without external dependencies."""
    data = Path(path).read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a valid PNG file: {path}")
    return struct.unpack(">II", data[16:24])


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render one local HTML file to one PNG.")
    parser.add_argument("--html", required=True, help="Path to standalone HTML file.")
    parser.add_argument("--png", required=True, help="Output PNG path.")
    parser.add_argument("--selector", default="#image-root", help="CSS selector to screenshot.")
    parser.add_argument("--width", type=int, default=1080, help="Viewport width.")
    parser.add_argument("--height", type=int, default=1440, help="Viewport height.")
    parser.add_argument(
        "--device-scale-factor",
        type=float,
        default=1,
        help="Playwright device scale factor.",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Reserved for compatibility; the selector must still match exactly one element.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    try:
        result = render_html_file(
            args.html,
            args.png,
            selector=args.selector,
            width=args.width,
            height=args.height,
            device_scale_factor=args.device_scale_factor,
            full_page=args.full_page,
        )
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
