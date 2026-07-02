import financial_agent_runtime as runtime
from financial_agent_runtime import tool_access
import thesis_tracker_agent.config as config_module
from thesis_tracker_agent import tools
from thesis_tracker_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)


def test_thesis_prompt_defines_artifact_root():
    prompt = (PROJECT_ROOT / "agents" / "thesis.md").read_text(encoding="utf-8")
    assert "若 task 描述提供了上游产物根目录" in prompt


def test_default_config_resolves_from_outside_project(monkeypatch, tmp_path):
    for env_name in [
        "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY",
        "ARK_API_KEY",
    ]:
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", tmp_path / "missing.env")
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "thesis"
    assert WORKSPACE_ROOT == PROJECT_ROOT.parent
    assert cfg.output.dir == "./out"
    assert "ifind-stock" in cfg.mcp
    assert "ifind-fund" in cfg.mcp
    assert "ifind-edb" in cfg.mcp
    assert "ifind-news" in cfg.mcp
    assert "ifind-bond" in cfg.mcp
    assert "ifind-global-stock" in cfg.mcp
    assert "ifind-index" in cfg.mcp
    assert "mx-ds-mcp" in cfg.mcp


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

    assert (
        server_configs["ifind-stock"]["headers"]["Authorization"]
        == "Bearer shared-token"
    )
    assert (
        server_configs["ifind-news"]["headers"]["Authorization"]
        == "Bearer shared-token"
    )


def test_mx_ds_auth_and_default_group_allowlist(monkeypatch, tmp_path):
    monkeypatch.delenv("TOOL_CONCURRENCY_CONFIG", raising=False)
    tool_access._ACCESS_CONFIG_CACHE.clear()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: https://example.test/stock
    transport: streamable_http
  mx-ds-mcp:
    url: https://mxapi.eastmoney.com/mxds/mcp
    transport: streamable-http
    connectTimeout: 10
    timeout: 120
    headers:
      em_api_key: "${MX_DS_MCP_API_KEY}"
""",
        encoding="utf-8",
    )
    tool_config_path = tmp_path / "tool-concurrency.yaml"
    tool_config_path.write_text(
        """
tool_groups:
  test_mcp:
    source: mcp
    servers:
      - mx-ds-mcp
agent_tools:
  thesis_tracker:
    tool_groups:
      - test_mcp
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("TOOL_CONCURRENCY_CONFIG", str(tool_config_path))
    monkeypatch.setenv("MX_DS_MCP_API_KEY", "mx-key")

    cfg = load_config(str(config_path))
    access_config = runtime.load_tool_access_config(None)
    server_names = runtime.mcp_server_names_for_tool_group(
        access_config,
        "test_mcp",
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)

    assert set(server_configs) == {"mx-ds-mcp"}
    assert server_configs["mx-ds-mcp"]["transport"] == "streamable_http"
    assert server_configs["mx-ds-mcp"]["headers"] == {"em_api_key": "mx-key"}
    assert server_configs["mx-ds-mcp"]["timeout"] == 120
    assert cfg.mcp["mx-ds-mcp"].connect_timeout == 10


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


def test_orchestrator_output_dir_is_used_exactly(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))
    monkeypatch.delenv("THESIS_TRACKER_OUTPUT_TIMESTAMP", raising=False)

    output_dir = storage_root / "out" / "20260625-101500" / "thesis"
    out_path = tools.create_task_output_dir.invoke({"output_dir": str(output_dir)})
    md_path = tools.write_markdown_report.invoke(
        {
            "title": "Test Thesis",
            "markdown": "# Thesis\n",
            "output_dir": str(output_dir),
        }
    )
    json_path = tools.write_json_artifact.invoke(
        {
            "data_json": '{"ticker": "600519.SH"}',
            "filename": "thesis.json",
            "output_dir": str(output_dir),
        }
    )

    assert out_path == "out/20260625-101500/thesis"
    assert md_path == "out/20260625-101500/thesis/test-thesis.md"
    assert json_path == "out/20260625-101500/thesis/thesis.json"
    assert not any(path.is_dir() for path in output_dir.glob("20??????-??????*"))
