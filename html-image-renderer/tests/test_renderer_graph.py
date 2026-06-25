from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
SKILLS_DIR = PROJECT_ROOT / "skills"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def test_graph_imports_in_test_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("HTML_IMAGE_RENDERER_TEST_MODE", "1")
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    sys.modules.pop("html_image_renderer_agent.graph", None)

    graph_module = importlib.import_module("html_image_renderer_agent.graph")

    assert graph_module.graph["name"] == "html_image_renderer"
    assert graph_module.graph["test_mode"] is True
    assert graph_module.graph["backend_type"] == "localshell"
    assert graph_module.graph["backend_root"] == str(tmp_path.resolve())
    assert graph_module.graph["skills"] == [str(SKILLS_DIR)]


def test_backend_root_is_shared_storage_root(monkeypatch, tmp_path):
    pytest.importorskip("deepagents")
    monkeypatch.setenv("HTML_IMAGE_RENDERER_TEST_MODE", "1")
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    sys.modules.pop("html_image_renderer_agent.graph", None)
    graph_module = importlib.import_module("html_image_renderer_agent.graph")

    backend = graph_module._create_backend()

    assert backend.cwd == tmp_path.resolve()
    assert backend.virtual_mode is False


def test_relative_output_base_uses_shared_storage_root(monkeypatch, tmp_path):
    from html_image_renderer_agent.config import resolve_output_base

    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))

    assert resolve_output_base("./out") == (tmp_path / "out").resolve()


def test_html_anything_skills_are_mounted():
    expected = [
        "finance-report",
        "data-report",
        "magazine-poster",
        "poster-hero",
        "deck-swiss-international",
    ]

    for skill_id in expected:
        assert (SKILLS_DIR / skill_id / "SKILL.md").exists(), skill_id
        assert (SKILLS_DIR / skill_id / "example.html").exists(), skill_id

    skill_dirs = [p for p in SKILLS_DIR.iterdir() if p.is_dir()]
    assert len(skill_dirs) >= 70


def test_old_single_image_skill_assets_are_removed():
    old_skill_id = "html-anything-" + "single-image"
    assert not (SKILLS_DIR / old_skill_id).exists()

    searched_roots = [
        PROJECT_ROOT / "agents",
        PROJECT_ROOT / "src",
    ]
    forbidden = [
        old_skill_id,
        "guizang-social-" + "card-skill",
        "template-swiss-" + "card",
        "template-editorial-" + "card",
        "single-image-" + "routing",
        "validate-social-" + "deck",
    ]
    hits: list[str] = []
    for root in searched_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix in {".pyc", ".png", ".webp"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in forbidden:
                if token in text:
                    hits.append(f"{path.relative_to(PROJECT_ROOT)}: {token}")

    assert not hits


def test_renderer_prompt_contains_skill_selection_rules():
    prompt = (PROJECT_ROOT / "agents" / "html-image-renderer.md").read_text(
        encoding="utf-8"
    )

    assert "source_paths" in prompt
    assert "Always read `source_paths` yourself" in prompt
    assert "finance-report" in prompt
    assert "data-report" in prompt
    assert "magazine-poster" in prompt
    assert "poster-hero" in prompt
    assert "deck-swiss-international" in prompt
    assert "single static image" in prompt
    assert "exactly one element matching" in prompt
    assert "`#image-root`" in prompt
    assert "Never ask the orchestrator to paste full file contents" in prompt
    assert "read the selected skill's full `SKILL.md`" in prompt
    assert "example.html" in prompt
    assert "limit=220" in prompt
    assert "Do not load a large `example.html` wholesale" in prompt
    assert "shared design directives + selected SKILL.md body + user content" in prompt
    assert "data-html-anything-skill" in prompt
    assert "generic dark financial dashboard" in prompt
    assert "Keep the final response terse" in prompt
    assert "Do not invent calendar fields" in prompt
    assert "output_dir/html/" in prompt
    assert "output_dir/png/" in prompt
    assert "three-digit sequence numbers" in prompt
    assert "html/002.html` pairs with `png/002.png" in prompt
    assert "treat it as your artifact root" in prompt
    assert "do not create a new top-level" in prompt


def test_runtime_context_exposes_html_anything_skills(monkeypatch, tmp_path):
    monkeypatch.setenv("HTML_IMAGE_RENDERER_TEST_MODE", "1")
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    sys.modules.pop("html_image_renderer_agent.graph", None)
    graph_module = importlib.import_module("html_image_renderer_agent.graph")
    cfg = graph_module.load_config()

    context = graph_module._runtime_context_prompt(cfg)

    assert f"Shared file storage root: {tmp_path.resolve()}" in context
    assert f"Default output base directory: {(tmp_path / 'out').resolve()}" in context
    assert "HTML Anything skills directory:" in context
    assert str(SKILLS_DIR) in context
    assert "HTML render helper script:" in context
    assert "#image-root" in context
    assert "read its SKILL.md" in context
    assert "example.html in bounded structural slices" in context
    assert "data-html-anything-skill" in context
    assert "html/<seq>.html and png/<seq>.png" in context
    assert "html/001.html" in context
    assert "png/001.png" in context
    assert "Never overwrite an existing sequence" in context
    assert "treat it as your artifact root" in context
    assert "do not create a new top-level out/<timestamp>/ folder" in context
    assert "seed template" not in context
    assert "routing reference" not in context


def test_graph_mounts_skills_directory_in_source():
    import html_image_renderer_agent.graph as graph_module

    source = Path(graph_module.__file__).read_text(encoding="utf-8")

    assert "skills=[str(SKILLS_DIR)]" in source
    assert "html-anything-" + "single-image" not in source


def test_load_source_texts_reads_md_and_csv(tmp_path):
    from html_image_renderer_agent.render_html import load_source_texts

    md_path = tmp_path / "note.md"
    csv_path = tmp_path / "signals.csv"
    md_path.write_text("# Morning Note\n\nTop call: neutral warm.\n", encoding="utf-8")
    csv_path.write_text("ticker,signal\n000001,buy watch\n", encoding="utf-8")

    loaded = load_source_texts([str(md_path), str(csv_path)])

    assert loaded[str(md_path.resolve())].startswith("# Morning Note")
    assert "000001,buy watch" in loaded[str(csv_path.resolve())]


def test_validate_html_contract_requires_skill_provenance(tmp_path):
    from html_image_renderer_agent.render_html import validate_html_contract

    html_path = tmp_path / "index.html"
    html_path.write_text(
        """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Missing Skill</title></head>
<body><main id="image-root">No provenance</main></body>
</html>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="data-html-anything-skill"):
        validate_html_contract(html_path)


def test_validate_html_contract_rejects_remote_resources(tmp_path):
    from html_image_renderer_agent.render_html import validate_html_contract

    html_path = tmp_path / "index.html"
    html_path.write_text(
        """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Remote</title></head>
<body>
<main id="image-root" data-html-anything-skill="deck-swiss-international">
  <img src="https://example.com/chart.png" alt="">
</main>
</body>
</html>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="remote resources"):
        validate_html_contract(html_path)


def test_render_html_requires_one_image_root(tmp_path):
    from html_image_renderer_agent.render_html import render_html_file

    out_dir = tmp_path / "out" / "20260623-090000"
    html_path = out_dir / "html" / "001.html"
    png_path = out_dir / "png" / "001.png"
    html_path.parent.mkdir(parents=True)
    png_path.parent.mkdir(parents=True)
    html_path.write_text(
        """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Bad Contract</title></head>
<body><main>No image root</main></body>
</html>
""",
        encoding="utf-8",
    )

    try:
        with pytest.raises(ValueError, match="Expected exactly one element"):
            render_html_file(html_path, png_path, selector="#image-root")
    except RuntimeError as exc:
        if "playwright install chromium" in str(exc):
            pytest.skip(str(exc))
        raise


def test_render_html_to_single_png(tmp_path):
    from html_image_renderer_agent.render_html import render_html_file

    md_path = tmp_path / "note.md"
    csv_path = tmp_path / "signals.csv"
    md_path.write_text("# Morning Note\n\nTop call: neutral warm.\n", encoding="utf-8")
    csv_path.write_text("ticker,signal\n000001,buy watch\n", encoding="utf-8")

    out_dir = tmp_path / "out" / "20260623-090000"
    html_path = out_dir / "html" / "001.html"
    png_path = out_dir / "png" / "001.png"
    html_path.parent.mkdir(parents=True)
    png_path.parent.mkdir(parents=True)
    html_path.write_text(
        """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Renderer Smoke</title>
<style>
  html, body { margin: 0; padding: 0; background: #eceff3; }
  #image-root {
    width: 640px;
    height: 360px;
    box-sizing: border-box;
    padding: 36px;
    background: #f8fafc;
    color: #0f172a;
    font-family: system-ui, -apple-system, "PingFang SC", sans-serif;
    border: 1px solid #cbd5e1;
  }
  h1 { margin: 0 0 18px; font-size: 42px; line-height: 1.05; }
  p { margin: 0; font-size: 22px; line-height: 1.45; }
</style>
</head>
<body>
<main id="image-root" data-html-anything-skill="deck-swiss-international">
  <h1>盘前日报头图</h1>
  <p>Source files: note.md + signals.csv</p>
  <p>Top call: neutral warm.</p>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )

    try:
        result = render_html_file(
            html_path,
            png_path,
            selector="#image-root",
            width=640,
            height=360,
        )
    except RuntimeError as exc:
        if "playwright install chromium" in str(exc):
            pytest.skip(str(exc))
        raise

    assert result["png_path"] == str(png_path.resolve())
    assert result["width"] == 640
    assert result["height"] == 360
    assert png_path.exists()
    assert png_path.stat().st_size > 0

    pngs = list((out_dir / "png").glob("*.png"))
    assert pngs == [png_path]
