import importlib

import financial_agent_runtime as runtime
from financial_agent_runtime import tool_access
import stock_screen_agent.config as config_module
from stock_screen_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)
from stock_screen_agent import tools


def _write_tool_access_config(path, text: str):
    cfg = path / "tool-concurrency.yaml"
    cfg.write_text(text, encoding="utf-8")
    tool_access._ACCESS_CONFIG_CACHE.clear()
    return cfg


def test_screen_prompt_defines_artifact_root():
    prompt = (PROJECT_ROOT / "agents" / "screen.md").read_text(encoding="utf-8")
    skill = (PROJECT_ROOT / "skills" / "idea-generation" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "artifact root / output directory" in prompt
    assert "If no directory is provided (standalone" in prompt
    assert "upstream output directory" in skill
    assert "do not create a new top-level" in skill


def test_default_config_resolves_from_project_root(monkeypatch, tmp_path):
    for env_name in [
        "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY",
        "ARK_API_KEY",
    ]:
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", tmp_path / "missing.env")
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "screen"
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


def test_shared_ifind_credential_applies_to_all_ifind_servers(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: https://stock.example/mcp
    transport: streamable_http
  ifind-news:
    url: https://news.example/mcp
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


def test_mx_ds_credential_and_tool_group_allowlist(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: https://stock.example/mcp
    transport: streamable_http
  ifind-news:
    url: https://news.example/mcp
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
    tool_config_path = _write_tool_access_config(
        tmp_path,
        """
tool_groups:
  test_mcp:
    source: mcp
    servers:
      - ifind-news
      - mx-ds-mcp
agent_tools:
  stock_screen:
    tool_groups:
      - test_mcp
""",
    )
    monkeypatch.setenv("TOOL_CONCURRENCY_CONFIG", str(tool_config_path))
    monkeypatch.setenv("IFIND_MCP_TOKEN", "shared-token")
    monkeypatch.setenv("MX_DS_MCP_API_KEY", "mx-key")

    cfg = load_config(str(config_path))
    access_config = runtime.load_tool_access_config(None)
    server_names = runtime.mcp_server_names_for_tool_group(
        access_config,
        "test_mcp",
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)

    assert set(server_configs) == {"ifind-news", "mx-ds-mcp"}
    assert (
        server_configs["ifind-news"]["headers"]["Authorization"]
        == "Bearer shared-token"
    )
    assert server_configs["mx-ds-mcp"] == {
        "url": "https://mxapi.eastmoney.com/mxds/mcp",
        "transport": "streamable_http",
        "headers": {"em_api_key": "mx-key"},
        "timeout": 120,
    }
    assert cfg.mcp["mx-ds-mcp"].connect_timeout == 10


def test_workspace_root_env_file_is_loaded(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: https://stock.example/mcp
    transport: streamable_http
""",
        encoding="utf-8",
    )
    env_path = tmp_path / ".env"
    env_path.write_text("IFIND_MCP_TOKEN=workspace-token\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", env_path)
    monkeypatch.delenv("IFIND_MCP_AUTHORIZATION", raising=False)
    monkeypatch.delenv("IFIND_MCP_TOKEN", raising=False)

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert (
        server_configs["ifind-stock"]["headers"]["Authorization"]
        == "Bearer workspace-token"
    )


def test_timestamped_output_dir_is_workspace_relative(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.delenv("AGENT_FILE_STORAGE_ROOT", raising=False)
    monkeypatch.setenv("STOCK_SCREEN_OUTPUT_TIMESTAMP", "20260602-150000")

    out_dir = tools._timestamped_output_dir("./out")
    same_out_dir = tools._timestamped_output_dir("./out")
    explicit_dir = tools._timestamped_output_dir("./out/20260602-151500")

    assert out_dir == WORKSPACE_ROOT / "out" / "20260602-150000"
    assert out_dir.exists()
    assert same_out_dir == out_dir
    assert explicit_dir == WORKSPACE_ROOT / "out" / "20260602-151500"


def test_agent_file_storage_root_controls_output_dir(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("STOCK_SCREEN_OUTPUT_TIMESTAMP", "20260602-160000")

    out_dir = tools._timestamped_output_dir("./out")
    markdown_path = tools.write_markdown_report.invoke(
        {"markdown": "# Screen\n", "filename": "screen.md", "output_dir": "./out"}
    )

    assert file_storage_root() == storage_root
    assert out_dir == storage_root / "out" / "20260602-160000"
    assert markdown_path == "out/20260602-160000/screen.md"
    assert (storage_root / markdown_path).read_text(encoding="utf-8") == "# Screen\n"


def test_write_artifacts_return_workspace_relative_paths(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.delenv("AGENT_FILE_STORAGE_ROOT", raising=False)
    monkeypatch.setenv("STOCK_SCREEN_OUTPUT_TIMESTAMP", "20260602-153000")

    out_path = tools.create_task_output_dir.invoke({"output_dir": "./out"})
    markdown_path = tools.write_markdown_report.invoke(
        {"markdown": "# Screen\n", "filename": "screen.md", "output_dir": "./out"}
    )
    json_path = tools.write_json_artifact.invoke(
        {
            "data_json": '{"ticker": "600519.SH"}',
            "filename": "screen.json",
            "output_dir": "./out",
        }
    )

    assert out_path == "out/20260602-153000"
    assert markdown_path == "out/20260602-153000/screen.md"
    assert json_path == "out/20260602-153000/screen.json"
    assert (WORKSPACE_ROOT / markdown_path).exists()
    assert (WORKSPACE_ROOT / json_path).exists()


def test_orchestrator_output_dir_is_used_exactly(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))
    monkeypatch.delenv("STOCK_SCREEN_OUTPUT_TIMESTAMP", raising=False)

    output_dir = storage_root / "out" / "20260625-101500" / "screen"
    out_path = tools.create_task_output_dir.invoke({"output_dir": str(output_dir)})
    markdown_path = tools.write_markdown_report.invoke(
        {
            "markdown": "# Screen\n",
            "filename": "screen.md",
            "output_dir": str(output_dir),
        }
    )
    json_path = tools.write_json_artifact.invoke(
        {
            "data_json": '{"ticker": "600519.SH"}',
            "filename": "screen.json",
            "output_dir": str(output_dir),
        }
    )

    assert out_path == "out/20260625-101500/screen"
    assert markdown_path == "out/20260625-101500/screen/screen.md"
    assert json_path == "out/20260625-101500/screen/screen.json"
    assert not any(path.is_dir() for path in output_dir.glob("20??????-??????*"))


def test_timestamp_detection_ignores_grandparent_timestamp(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("STOCK_SCREEN_OUTPUT_TIMESTAMP", "20260625-111111")

    output_dir = storage_root / "out" / "20260625-101500" / "screen" / "nested"
    out_path = tools.create_task_output_dir.invoke({"output_dir": str(output_dir)})

    assert out_path == "out/20260625-101500/screen/nested/20260625-111111"


def test_graph_imports_in_test_mode(monkeypatch):
    monkeypatch.setenv("STOCK_SCREEN_TEST_MODE", "1")
    module = importlib.import_module("stock_screen_agent.graph")

    assert module.graph == {
        "name": "stock_screen",
        "test_mode": True,
        "backend_type": "filesystem",
    }
