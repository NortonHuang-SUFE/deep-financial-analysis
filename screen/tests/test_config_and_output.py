import importlib

import stock_screen_agent.config as config_module
from stock_screen_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)
from stock_screen_agent import tools


def test_default_config_resolves_from_project_root(monkeypatch, tmp_path):
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

    assert PROJECT_ROOT.name == "screen"
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

    assert server_configs["ifind-stock"]["headers"]["Authorization"] == "Bearer shared-token"
    assert server_configs["ifind-news"]["headers"]["Authorization"] == "Bearer shared-token"


def test_workspace_root_env_file_is_loaded(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
model:
  default: yaml-model
  base_url: https://dashscope.aliyuncs.com/compatible-mode
mcp: {}
""",
        encoding="utf-8",
    )
    env_path = tmp_path / ".env"
    env_path.write_text("MODEL_NAME=workspace-env-model\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", env_path)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    cfg = load_config(str(config_path))

    assert cfg.model.default == "workspace-env-model"


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


def test_graph_imports_in_test_mode(monkeypatch):
    monkeypatch.setenv("STOCK_SCREEN_TEST_MODE", "1")
    module = importlib.import_module("stock_screen_agent.graph")

    assert module.graph == {
        "name": "stock_screen",
        "test_mode": True,
        "backend_type": "filesystem",
    }
