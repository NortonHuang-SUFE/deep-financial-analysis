import sector_research_agent.config as config_module
from sector_research_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    load_config,
)
from sector_research_agent import tools


def _clear_env(monkeypatch):
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
        "IFIND_MCP_AUTHORIZATION",
        "IFIND_MCP_TOKEN",
        "IFIND_STOCK_MCP_AUTHORIZATION",
        "IFIND_STOCK_MCP_TOKEN",
        "IFIND_NEWS_MCP_AUTHORIZATION",
        "IFIND_NEWS_MCP_TOKEN",
        "SECTOR_RESEARCH_DISABLE_MCP",
        "SECTOR_RESEARCH_OUTPUT_TIMESTAMP",
    ]:
        monkeypatch.delenv(env_name, raising=False)


def test_default_config_resolves_from_project_root(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", tmp_path / "missing.env")
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "sector"
    assert WORKSPACE_ROOT.name == "financialServicesModified"
    assert cfg.model.default == "qwen-3.7-max"
    assert cfg.model.base_url == "https://dashscope.aliyuncs.com/compatible-mode"
    assert cfg.output.dir == "./out"
    assert "ifind-stock" in cfg.mcp
    assert cfg.mcp["ifind-stock"].url


def test_workspace_env_and_process_env_override_ifind_auth(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    workspace_env = tmp_path / ".env"
    workspace_env.write_text("IFIND_MCP_TOKEN=from-workspace-env\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", workspace_env)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: "https://example.test/stock"
    transport: "streamable_http"
    token: ""
    headers: {}
  ifind-news:
    url: "https://example.test/news"
    transport: "streamable_http"
    token: ""
    headers: {}
""",
        encoding="utf-8",
    )

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"] == {
        "Authorization": "Bearer from-workspace-env"
    }

    monkeypatch.setenv("IFIND_MCP_AUTHORIZATION", "from-process-env")
    monkeypatch.setenv("IFIND_NEWS_MCP_AUTHORIZATION", "from-news-env")
    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"] == {
        "Authorization": "from-process-env"
    }
    assert server_configs["ifind-news"]["headers"] == {
        "Authorization": "from-news-env"
    }


def test_timestamped_output_dir_is_workspace_relative(monkeypatch):
    _clear_env(monkeypatch)
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("SECTOR_RESEARCH_OUTPUT_TIMESTAMP", "20260602-120000")

    out_dir = tools._timestamped_output_dir("./out")
    same_out_dir = tools._timestamped_output_dir("./out")
    explicit_dir = tools._timestamped_output_dir("./out/20260602-130000")

    assert out_dir == WORKSPACE_ROOT / "out" / "20260602-120000"
    assert out_dir.exists()
    assert same_out_dir == out_dir
    assert explicit_dir == WORKSPACE_ROOT / "out" / "20260602-130000"


def test_graph_imports_in_test_mode(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SECTOR_RESEARCH_TEST_MODE", "1")
    import sector_research_agent.graph as graph_module

    assert graph_module.graph == {"name": "sector_research", "test_mode": True}
