from pathlib import Path

from thesis_tracker_agent import tools
from thesis_tracker_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    load_config,
)


def test_default_config_resolves_from_outside_project(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "thesis"
    assert WORKSPACE_ROOT == PROJECT_ROOT.parent
    assert cfg.model.default == "qwen-3.7-max"
    assert cfg.model.base_url == "https://dashscope.aliyuncs.com/compatible-mode"
    assert cfg.output.dir == "./out"
    assert "ifind-stock" in cfg.mcp
    assert "ifind-fund" in cfg.mcp
    assert "ifind-edb" in cfg.mcp
    assert "ifind-news" in cfg.mcp
    assert "ifind-bond" in cfg.mcp
    assert "ifind-global-stock" in cfg.mcp
    assert "ifind-index" in cfg.mcp


def test_ifind_auth_env_overrides_and_per_server_wins(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: https://example.test/stock
    transport: streamable_http
  ifind-news:
    url: https://example.test/news
    transport: streamable_http
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("IFIND_MCP_TOKEN", "shared-token")
    monkeypatch.setenv("IFIND_NEWS_MCP_AUTHORIZATION", "raw-news-auth")

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"]["Authorization"] == "Bearer shared-token"
    assert server_configs["ifind-news"]["headers"]["Authorization"] == "raw-news-auth"


def test_timestamped_output_dir_is_workspace_relative(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("THESIS_TRACKER_OUTPUT_TIMESTAMP", "20260602-120000")

    out_dir = tools._timestamped_output_dir("./out")
    same_out_dir = tools._timestamped_output_dir("./out")
    explicit_dir = tools._timestamped_output_dir("./out/20260602-130000")

    assert out_dir == WORKSPACE_ROOT / "out" / "20260602-120000"
    assert out_dir.exists()
    assert same_out_dir == out_dir
    assert explicit_dir == WORKSPACE_ROOT / "out" / "20260602-130000"


def test_write_artifacts_reuse_timestamp_dir(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("THESIS_TRACKER_OUTPUT_TIMESTAMP", "20260602-121500")

    md_path = tools.write_markdown_report.invoke(
        {"title": "Test Thesis", "markdown": "# Test\n"}
    )
    json_path = tools.write_json_artifact.invoke(
        {"data_json": '{"ticker": "600519.SH"}', "filename": "thesis.json"}
    )

    assert md_path == "out/20260602-121500/test-thesis.md"
    assert json_path == "out/20260602-121500/thesis.json"
    assert (WORKSPACE_ROOT / md_path).read_text(encoding="utf-8") == "# Test\n"
    assert (WORKSPACE_ROOT / json_path).exists()
