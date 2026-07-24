from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


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


def test_renderer_prefers_docker_chromium_env_path(monkeypatch):
    from html_image_renderer_agent.render_html import find_browser

    monkeypatch.setenv("HTML_IMAGE_RENDERER_BROWSER", "/usr/bin/chromium")
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/usr/bin/chromium")

    assert find_browser() == "/usr/bin/chromium"


def test_renderer_launch_args_are_container_friendly():
    from html_image_renderer_agent.render_html import CHROMIUM_LAUNCH_ARGS

    assert "--no-sandbox" in CHROMIUM_LAUNCH_ARGS
    assert "--disable-dev-shm-usage" in CHROMIUM_LAUNCH_ARGS


def test_html_anything_skills_are_mounted():
    expected = [
        "finance-report",
        "data-report",
        "magazine-poster",
        "poster-hero",
        "deck-swiss-international",
        "margin-trading-wechat-long-image",
    ]

    for skill_id in expected:
        assert (SKILLS_DIR / skill_id / "SKILL.md").exists(), skill_id
        assert (SKILLS_DIR / skill_id / "assets" / "example.html").exists(), skill_id

    skill_dirs = [p for p in SKILLS_DIR.iterdir() if p.is_dir()]
    assert len(skill_dirs) >= 70


def test_html_anything_skills_declare_example_assets():
    skill_dirs = [p for p in SKILLS_DIR.iterdir() if p.is_dir()]
    assert skill_dirs

    missing: list[str] = []
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        example_html = skill_dir / "assets" / "example.html"
        if not skill_md.exists() or not example_html.exists():
            missing.append(skill_dir.name)
            continue
        text = skill_md.read_text(encoding="utf-8")
        if "## Assets" not in text or "`assets/example.html`" not in text:
            missing.append(skill_dir.name)

    assert not missing


def test_margin_trading_wechat_long_image_skill_contract(tmp_path):
    from html_image_renderer_agent.render_html import validate_html_contract

    skill_id = "margin-trading-wechat-long-image"
    skill_dir = SKILLS_DIR / skill_id
    skill_md = skill_dir / "SKILL.md"
    example_html = skill_dir / "assets" / "example.html"
    richtext_example = skill_dir / "assets" / "example-richtext.html"
    logo = skill_dir / "assets" / "gtja-logo.png"
    qrcode = skill_dir / "assets" / "gtja-qrcode.jpg"
    richtext_validator = skill_dir / "scripts" / "validate_wechat_richtext.py"

    skill_text = skill_md.read_text(encoding="utf-8")
    _, frontmatter, _ = skill_text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)

    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == skill_id
    description = metadata["description"]
    for trigger in [
        "给融资融券公众号做长图",
        "两融聚焦长图",
        "融资融券公众号市场概览",
    ]:
        assert trigger in description
    assert "普通财报" in description
    assert "通用数据看板" in description
    assert "高度由内容和普通文档流自然撑开" in skill_text
    assert "不要预设总高度、最短高度或最长高度" in skill_text
    assert "以任务提示词和来源文件作为内容结构的唯一依据" in skill_text
    assert "标题、板块数量、板块名称、顺序、每部分内容" in skill_text
    assert "提示词没有要求表格或图表时，不要自行添加" in skill_text
    assert "数据表不是必需内容" in skill_text
    forbidden_example_sections = [
        "今日概要",
        "两融市场概览",
        "板块融资解码",
        "个股融资追踪",
        "ETF融资追踪",
    ]
    for example_section in forbidden_example_sections:
        assert example_section not in skill_text
    assert "richtext/<seq>.html" in skill_text
    # The three-artifact contract has to be visible before the workflow, so a
    # renderer that plans right after reading this file cannot miss it.
    assert "## 交付物（三件套，缺一即为失败运行）" in skill_text
    assert "richtext_path" in skill_text
    assert "这一步不可跳过" in skill_text
    assert skill_text.index("交付物（三件套") < skill_text.index("## 内容决策边界")
    assert "assets/example-richtext.html" in skill_text
    assert "validate_wechat_richtext.py" in skill_text
    assert "check_wechat_mobile.py" in skill_text
    assert "预览宽度不得超过 375px" in skill_text
    assert "移动端优先" in skill_text
    assert "text/html" in skill_text
    assert "table-layout:auto" in skill_text
    assert "长图和富文本都必须同时使用" in skill_text
    assert 'data-brand-asset="logo"' in skill_text
    assert 'data-brand-asset="qrcode"' in skill_text
    assert "1440×960" not in skill_text

    palette = [
        "#003377",
        "#103480",
        "#33a0e8",
        "#e6212a",
        "#239947",
        "#eeeeee",
        "#f3efff",
        "#f0f7ff",
    ]
    for color in palette:
        assert color in skill_text.lower()

    disclaimer = (
        "免责声明：本文内容均基于客观市场行情交易数据产生，"
        "数据来源于证券交易所官网公开数据，文中内容不构成任何投资建议，"
        "市场有风险，投资需谨慎。"
    )
    risk_warning = (
        "风险提示：融资融券交易有风险，投资者在参与融资融券交易前请务必阅读、"
        "了解和掌握有关法律法规和交易所、证券登记结算机构业务规则等相关规则和"
        "《风险揭示书》。"
    )
    qr_guide = "扫码关注国泰海通融资融券公众号 获取更多两融信息资讯"
    for required_text in [disclaimer, risk_warning, qr_guide]:
        assert required_text in skill_text

    mobile_checker = skill_dir / "scripts" / "check_wechat_mobile.py"
    required_assets = [
        example_html,
        richtext_example,
        logo,
        qrcode,
        richtext_validator,
        mobile_checker,
    ]
    for asset in required_assets:
        assert asset.exists(), asset
        assert asset.stat().st_size > 0, asset

    validation = subprocess.run(
        [sys.executable, str(richtext_validator), str(richtext_example)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert validation.returncode == 0, validation.stdout + validation.stderr
    example_validation = json.loads(validation.stdout)
    assert example_validation["valid"] is True
    assert example_validation["data_table_count"] == 0
    assert all(example_validation["required_compliance_texts"].values())

    no_table_html = """<!doctype html>
<html><head><style>#wechat-richtext { max-width: 375px; }</style></head><body>
<button id="copy-richtext">复制</button>
<div id="wechat-richtext"><section style="display:block;width:100%;">
<img src="data:image/png;base64,AA==" data-brand-asset="logo" width="300" style="width:300px;height:auto!important;">
<section style="font-size:20px;text-align:center;">提示词指定板块一</section>
<section style="font-size:15px;line-height:1.65;">提示词指定板块二</section>
<p>DISCLAIMER_PLACEHOLDER</p><p>RISK_WARNING_PLACEHOLDER</p>
<img src="data:image/jpeg;base64,AA==" data-brand-asset="qrcode" width="190" style="width:190px;height:auto!important;">
</section></div>
<script>
const content = document.getElementById('wechat-richtext');
const item = new ClipboardItem({
  'text/html': new Blob([content.innerHTML]),
  'text/plain': new Blob([content.innerText]),
});
</script></body></html>
"""
    no_table_html = no_table_html.replace(
        "DISCLAIMER_PLACEHOLDER", disclaimer
    ).replace("RISK_WARNING_PLACEHOLDER", risk_warning)
    no_table_path = tmp_path / "no-table.html"
    no_table_path.write_text(no_table_html, encoding="utf-8")
    no_table_validation = subprocess.run(
        [sys.executable, str(richtext_validator), str(no_table_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert no_table_validation.returncode == 0, no_table_validation.stdout
    no_table_result = json.loads(no_table_validation.stdout)
    assert no_table_result["valid"] is True
    assert no_table_result["data_table_count"] == 0
    assert all(no_table_result["required_compliance_texts"].values())

    invalid_table_path = tmp_path / "invalid-table.html"
    invalid_table_path.write_text(
        no_table_html.replace(
            '<section style="font-size:15px;line-height:1.65;">提示词指定板块二</section>',
            '<table style="width:100%;"><tr><th>字段</th></tr><tr><td>值</td></tr></table>',
        ),
        encoding="utf-8",
    )
    invalid_table_validation = subprocess.run(
        [sys.executable, str(richtext_validator), str(invalid_table_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid_table_validation.returncode == 1
    invalid_table_result = json.loads(invalid_table_validation.stdout)
    assert invalid_table_result["valid"] is False
    assert invalid_table_result["data_table_count"] == 1
    assert any("data table 1 must set inline" in error for error in invalid_table_result["errors"])

    # A fragment laid out for the 677px PC editor is what breaks on a phone, so
    # each way of smuggling a PC-width assumption in has to be rejected.
    mobile_regressions = {
        "pc-preview-width": (
            "#wechat-richtext { max-width: 375px; }",
            "#wechat-richtext { max-width: 677px; }",
            "preview max-width must be 375px or less",
        ),
        "fixed-wide-image": (
            'width="300" style="width:300px;height:auto!important;"',
            'width="620" style="width:620px;height:auto!important;"',
            "wider than the 300px a phone can show",
        ),
        "percentage-image-cap": (
            'width="300" style="width:300px;height:auto!important;"',
            'width="300" style="width:100%;max-width:88%;height:auto!important;"',
            "fractional percentage max-width",
        ),
        "uncapped-full-width-image": (
            'width="300" style="width:300px;height:auto!important;"',
            'width="300" style="width:100%;height:auto!important;"',
            "must also set an inline max-width in px",
        ),
    }
    for name, (original, replacement, expected_error) in mobile_regressions.items():
        broken_path = tmp_path / f"{name}.html"
        assert original in no_table_html, name
        broken_path.write_text(no_table_html.replace(original, replacement), encoding="utf-8")
        broken = subprocess.run(
            [sys.executable, str(richtext_validator), str(broken_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert broken.returncode == 1, (name, broken.stdout)
        broken_result = json.loads(broken.stdout)
        assert broken_result["valid"] is False, name
        assert any(expected_error in error for error in broken_result["errors"]), (
            name,
            broken_result["errors"],
        )

    richtext_html = richtext_example.read_text(encoding="utf-8")
    assert 'id="copy-richtext"' in richtext_html
    assert 'id="wechat-richtext"' in richtext_html
    assert "ClipboardItem" in richtext_html
    assert "'text/html'" in richtext_html
    assert "'text/plain'" in richtext_html
    assert 'data-brand-asset="logo"' in richtext_html
    assert 'data-brand-asset="qrcode"' in richtext_html
    assert "data:image/png;base64," in richtext_html
    assert "data:image/jpeg;base64," in richtext_html

    for role in ["logo", "qrcode"]:
        missing_role_path = tmp_path / f"missing-{role}-role.html"
        missing_role_path.write_text(
            richtext_html.replace(
                f'data-brand-asset="{role}"',
                'data-brand-asset="decorative"',
                1,
            ),
            encoding="utf-8",
        )
        missing_role_validation = subprocess.run(
            [sys.executable, str(richtext_validator), str(missing_role_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert missing_role_validation.returncode == 1
        assert f'data-brand-asset=\\"{role}\\"' in missing_role_validation.stdout

    for label, required_text in [
        ("disclaimer", disclaimer),
        ("risk_warning", risk_warning),
    ]:
        missing_compliance_path = tmp_path / f"missing-{label}.html"
        missing_compliance_path.write_text(
            richtext_html.replace(required_text, required_text[:-1], 1),
            encoding="utf-8",
        )
        missing_compliance_validation = subprocess.run(
            [
                sys.executable,
                str(richtext_validator),
                str(missing_compliance_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert missing_compliance_validation.returncode == 1
        missing_compliance_result = json.loads(missing_compliance_validation.stdout)
        assert missing_compliance_result["required_compliance_texts"][label] is False

    html = example_html.read_text(encoding="utf-8")
    contract = validate_html_contract(example_html)
    assert contract["skill"] == skill_id
    assert contract["image_root_count"] == 1

    assert 'src="./gtja-logo.png"' in html
    assert 'src="./gtja-qrcode.jpg"' in html
    assert 'data-brand-asset="logo"' in html
    assert 'data-brand-asset="qrcode"' in html
    assert "gtja-brand-lockup.png" not in html
    assert 'width: 1080px' in html
    image_root_css = html.split("#image-root {", 1)[1].split("}", 1)[0]
    assert "height:" not in image_root_css
    content_css = html.split(".content {", 1)[1].split("}", 1)[0]
    assert "height:" not in content_css
    assert "flex-direction: column" in html
    assert "<svg" not in html
    assert "<table" not in html
    assert "<canvas" not in html
    assert "<table" not in richtext_html
    assert "<svg" not in richtext_html
    assert "<canvas" not in richtext_html
    for example_section in forbidden_example_sections:
        assert example_section not in html
        assert example_section not in richtext_html
    for color in palette:
        assert color in html.lower()
    for color in [
        "#003377",
        "#103480",
        "#33a0e8",
        "#e6212a",
        "#239947",
        "#f3efff",
        "#f0f7ff",
    ]:
        assert color in richtext_html.lower()
    assert "--up: #e6212a" in html
    assert "--down: #239947" in html
    assert ".positive { color: var(--up); }" in html
    assert ".negative { color: var(--down); }" in html
    assert "▲" in html
    assert "▼" in html

    required_brand_content = [
        "任务提示词指定的主标题",
        "任务提示词指定的板块标题",
        disclaimer,
        risk_warning,
        qr_guide,
    ]
    for content in required_brand_content:
        assert content in html
        assert content in richtext_html

    assert "<h1>国泰海通</h1>" not in html
    assert ">国泰海通</p>" not in richtext_html


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
    assert "hard-coded" in prompt
    assert "scenario-to-skill list" in prompt
    assert "user's instruction" in prompt
    assert "artifacts you have actually read and analyzed" in prompt
    assert "target format or ratio" in prompt
    assert "publishing channel" in prompt
    assert "single static image" in prompt
    assert "exactly one element matching" in prompt
    assert "`#image-root`" in prompt
    assert "Never ask the orchestrator to paste full file contents" in prompt
    assert "read the selected skill's full `SKILL.md`" in prompt
    assert "follow its `## Assets` section" in prompt
    assert "assets/example.html" in prompt
    assert "limit=220" in prompt
    assert "Do not load a large `example.html` wholesale" in prompt
    assert "shared design directives + selected SKILL.md body + user content" in prompt
    assert "data-html-anything-skill" in prompt
    assert "light, bright, clear visual style" in prompt
    assert "red usually means up and green means down" in prompt
    assert "green usually means up and red means down" in prompt
    assert "generic dark financial dashboard" in prompt
    assert "Keep the final response terse" in prompt
    assert "Do not invent calendar fields" in prompt
    assert "output_dir/html/" in prompt
    assert "output_dir/png/" in prompt
    assert "three-digit sequence numbers" in prompt
    assert "html/002.html` pairs with `png/002.png" in prompt
    assert "treat it as your artifact root" in prompt
    assert "do not create a new top-level" in prompt
    assert "Visually inspect the actual rendered PNG before finishing" in prompt
    assert "PNG itself, not only its file metadata" in prompt
    assert "Only report the final accepted artifact set" in prompt
    assert "same-sequence companion files" in prompt
    assert "richtext_path" in prompt

    # The companion artifact was dropped from a real run because the agent
    # planned from this generic workflow instead of the selected skill's
    # artifact list, so the prompt has to force it into the todo list and
    # block a "success" report that omits it.
    assert "one item per declared" in prompt
    assert "output-constraints section" in prompt
    assert "## Completion Gate" in prompt
    assert "is a failed run" in prompt or "has failed" in prompt
    assert "ls -lR <output_dir>" in prompt
    # Image blocks survive tool-result eviction and are resent every turn, so
    # the QA loop is the renderer's dominant cost.
    assert "## QA Image Protocol" in prompt
    assert "do not slice a tall image into sections" in prompt
    assert "quality 75" in prompt
    assert "--device-scale-factor" in prompt
    assert "do not read the helper's source to discover flags" in prompt


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
    assert "follow its Assets section" in context
    assert "assets/example.html in bounded structural slices" in context
    assert "data-html-anything-skill" in context
    assert "visually inspect the actual PNG before finishing" in context
    assert "accepted PNG passes visual QA" in context
    assert "html/<seq>.html and png/<seq>.png" in context
    assert "html/001.html" in context
    assert "png/001.png" in context
    assert "Never overwrite an existing sequence" in context
    assert "treat it as your artifact root" in context
    assert "do not create a new top-level out/<timestamp>/ folder" in context
    assert "same-sequence companion artifact" in context
    assert "companion-validation status" in context
    assert "seed template" not in context
    assert "routing reference" not in context

    # Re-injected on every model call, so this is the strongest place to keep
    # the companion contract and the image-read budget in view.
    assert "## Deliverable Checklist" in context
    assert "one item per artifact the selected skill declares" in context
    assert "ls -lR <output_dir>" in context
    assert "is a failed run" in context
    assert "## QA Image Protocol" in context
    assert "do not read the same image twice" in context
    assert "## Render Helper Interface" in context
    assert "--device-scale-factor" in context


def test_runtime_context_uses_backend_render_helper_in_daytona(monkeypatch):
    monkeypatch.setenv("HTML_IMAGE_RENDERER_TEST_MODE", "1")
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    monkeypatch.setenv("DAYTONA_FILE_STORAGE_ROOT", "/home/daytona/financial-analysis")
    sys.modules.pop("html_image_renderer_agent.graph", None)
    graph_module = importlib.import_module("html_image_renderer_agent.graph")
    graph_module._RENDER_HELPER_BACKEND_PATH = None

    uploads: list[tuple[str, str]] = []
    monkeypatch.setattr(
        graph_module,
        "upload_file_artifact",
        lambda local_path, remote_path: uploads.append((str(local_path), str(remote_path))),
    )
    cfg = graph_module.load_config()

    context = graph_module._runtime_context_prompt(cfg)
    second_context = graph_module._runtime_context_prompt(cfg)

    expected = "/home/daytona/financial-analysis/.helpers/html-image-renderer/render_html.py"
    assert f"HTML render helper script: {expected}" in context
    assert f"HTML render helper script: {expected}" in second_context
    assert len(uploads) == 1
    assert uploads[0][0].endswith("html_image_renderer_agent/render_html.py")
    assert uploads[0][1] == expected


def test_graph_mounts_skills_directory_in_source():
    import html_image_renderer_agent.graph as graph_module

    source = Path(graph_module.__file__).read_text(encoding="utf-8")

    assert "skills=[mirror_skills_into_backend(backend, SKILLS_DIR)]" in source
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
