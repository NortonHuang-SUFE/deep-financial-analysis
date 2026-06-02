#!/usr/bin/env python3
"""Render a guizang-style HTML deck to numbered slide PNGs.

The script prefers an installed system Chrome/Edge so it does not require
Playwright's bundled browser download. It captures each `.slide` at 16:9 by
moving the deck container horizontally, matching the deck's presentation model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_BROWSER_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


def browser_path(explicit: str | None) -> str | None:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"Browser executable not found: {path}")
        return str(path)
    for candidate in DEFAULT_BROWSER_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an HTML slide deck to one PNG per slide.")
    parser.add_argument("html_file", help="Path to deck index.html.")
    parser.add_argument("output_dir", help="Directory for rendered 01.png, 02.png, ...")
    parser.add_argument("--browser", help="Chrome/Edge executable path. Defaults to installed system browser.")
    parser.add_argument("--width", type=int, default=1920, help="Viewport width.")
    parser.add_argument("--height", type=int, default=1080, help="Viewport height.")
    parser.add_argument("--delay-ms", type=int, default=250, help="Wait after moving to each slide.")
    args = parser.parse_args()

    html_file = Path(args.html_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not html_file.exists():
        print(f"ERROR: HTML file not found: {html_file}", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright is required. Install it in the project virtualenv.", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    executable = browser_path(args.browser)

    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if executable:
            launch_kwargs["executable_path"] = executable
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(device_scale_factor=1, viewport={"width": args.width, "height": args.height})

        page.add_init_script(
            "localStorage.setItem('guizang-ppt-low-power','1');"
        )
        page.goto(html_file.as_uri(), wait_until="networkidle")
        page.wait_for_load_state("domcontentloaded")
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")

        slide_count = page.locator(".slide").count()
        if slide_count == 0:
            browser.close()
            print("ERROR: no .slide elements found.", file=sys.stderr)
            return 1

        page.evaluate(
            """() => {
              document.body.classList.add('low-power');
              const deck = document.querySelector('#deck');
              if (deck) deck.style.transition = 'none';
              document.querySelectorAll('[data-anim]').forEach(el => {
                el.style.opacity = '1';
                el.style.transform = 'none';
              });
            }"""
        )

        for idx in range(slide_count):
            page.evaluate(
                """(idx) => {
                  const deck = document.querySelector('#deck');
                  if (deck) deck.style.transform = `translateX(${-idx * 100}vw)`;
                  window.dispatchEvent(new Event('resize'));
                }""",
                idx,
            )
            page.wait_for_timeout(args.delay_ms)
            page.screenshot(path=str(output_dir / f"{idx + 1:02d}.png"), full_page=False)

        browser.close()

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

