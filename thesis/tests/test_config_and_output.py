from pathlib import Path

import thesis_tracker_agent.config as config_module
from thesis_tracker_agent import tools
from thesis_tracker_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)


def test_default_config_resolves_from_outside_project(monkeypatch, tmp_path):
    for env_name in [
        "MODEL_NAME",
        "MODEL_GATEWAY_BASE_URL",
        "MODEL_GATEWAY_API_KEY",
        "MODEL_RELAY_BASE_URL",
        "MODEL_RELAY_API_KEY",
        "MODEL_BASE_URL",
        "MODEL_API_KEY",
        "MODEL_THINKING",
        "MODEL_MAX_TOKENS",
        "DASHSCOPE_API_KEY",
        "ALIBABA_API_KEY",
    ]:
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", tmp_path / "missing.env")
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


def test_shared_ifind_auth_applies_to_all_ifind_servers(monkeypatch, tmp_path):
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

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"]["Authorization"] == "Bearer shared-token"
    assert server_configs["ifind-news"]["headers"]["Authorization"] == "Bearer shared-token"


def test_timestamped_output_dir_is_workspace_relative(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.delenv("AGENT_FILE_STORAGE_ROOT", raising=False)
    monkeypatch.setenv("THESIS_TRACKER_OUTPUT_TIMESTAMP", "20260602-120000")

    out_dir = tools._timestamped_output_dir("./out")
    same_out_dir = tools._timestamped_output_dir("./out")
    explicit_dir = tools._timestamped_output_dir("./out/20260602-130000")

    assert out_dir == WORKSPACE_ROOT / "out" / "20260602-120000"
    assert out_dir.exists()
    assert same_out_dir == out_dir
    assert explicit_dir == WORKSPACE_ROOT / "out" / "20260602-130000"


def test_agent_file_storage_root_controls_output_dir(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("THESIS_TRACKER_OUTPUT_TIMESTAMP", "20260602-131500")

    out_dir = tools._timestamped_output_dir("./out")
    markdown_path = tools.write_markdown_report.invoke(
        {"title": "Test Thesis", "markdown": "# Thesis\n"}
    )

    assert file_storage_root() == storage_root
    assert out_dir == storage_root / "out" / "20260602-131500"
    assert markdown_path == "out/20260602-131500/test-thesis.md"
    assert (storage_root / markdown_path).read_text(encoding="utf-8") == "# Thesis\n"


def test_write_artifacts_reuse_timestamp_dir(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.delenv("AGENT_FILE_STORAGE_ROOT", raising=False)
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
