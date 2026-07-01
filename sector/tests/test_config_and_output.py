import financial_agent_runtime as runtime
import sector_research_agent.config as config_module
from sector_research_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)
from sector_research_agent import tools


def test_sector_prompt_defines_artifact_root():
    prompt = (PROJECT_ROOT / "agents" / "sector.md").read_text(encoding="utf-8")
    skill = (PROJECT_ROOT / "skills" / "sector-overview" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "若 task 描述提供了上游产物根目录" in prompt
    assert "若 task 描述提供了上游产物根目录" in skill
    assert "不要再调用 `create_task_output_dir`" in skill


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
        "MX_DS_MCP_API_KEY",
        "MX_DS_MCP_URL",
        "MX_DS_MCP_TRANSPORT",
        "AGENT_FILE_STORAGE_ROOT",
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
    assert "mx-ds-mcp" in cfg.mcp
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
  ifind-news:
    url: "https://example.test/news"
    transport: "streamable_http"
""",
        encoding="utf-8",
    )

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"] == {
        "Authorization": "Bearer from-workspace-env"
    }

    monkeypatch.setenv("IFIND_MCP_AUTHORIZATION", "from-process-env")
    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"] == {
        "Authorization": "from-process-env"
    }
    assert server_configs["ifind-news"]["headers"] == {
        "Authorization": "from-process-env"
    }


def test_mx_ds_auth_and_group_allowlist(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: "https://example.test/stock"
    transport: "streamable_http"
  mx-ds-mcp:
    url: "https://mxapi.eastmoney.com/mxds/mcp"
    transport: "streamable-http"
    connectTimeout: 10
    timeout: 120
    headers:
      em_api_key: "${MX_DS_MCP_API_KEY}"
mcp_tool_groups:
  default:
    servers:
      - mx-ds-mcp
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("MX_DS_MCP_API_KEY", "mx-key")

    cfg = load_config(str(config_path))
    server_names = runtime.mcp_tool_group_server_names(
        cfg.mcp_tool_groups,
        "default",
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)

    assert set(server_configs) == {"mx-ds-mcp"}
    assert server_configs["mx-ds-mcp"]["headers"] == {"em_api_key": "mx-key"}
    assert server_configs["mx-ds-mcp"]["timeout"] == 120
    assert cfg.mcp["mx-ds-mcp"].connect_timeout == 10


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


def test_agent_file_storage_root_controls_output_dir(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("SECTOR_RESEARCH_OUTPUT_TIMESTAMP", "20260602-140000")

    out_dir = tools._timestamped_output_dir("./out")
    markdown_path = tools.write_markdown_report.invoke(
        {
            "filename": "sector.md",
            "markdown": "# Sector\n",
            "output_dir": "./out",
        }
    )

    assert file_storage_root() == storage_root
    assert out_dir == storage_root / "out" / "20260602-140000"
    assert markdown_path == "out/20260602-140000/sector.md"
    assert (storage_root / markdown_path).read_text(encoding="utf-8") == "# Sector\n"


def test_orchestrator_output_dir_is_used_exactly(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    tools._TASK_OUTPUT_DIRS.clear()
    storage_root = tmp_path / "clean-storage"
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(storage_root))

    output_dir = storage_root / "out" / "20260625-101500" / "sector"
    out_path = tools.create_task_output_dir.invoke({"output_dir": str(output_dir)})
    markdown_path = tools.write_markdown_report.invoke(
        {
            "filename": "sector.md",
            "markdown": "# Sector\n",
            "output_dir": str(output_dir),
        }
    )
    json_path = tools.write_json_artifact.invoke(
        {
            "filename": "sector.json",
            "data_json": '{"sector": "banking"}',
            "output_dir": str(output_dir),
        }
    )

    assert out_path == "out/20260625-101500/sector"
    assert markdown_path == "out/20260625-101500/sector/sector.md"
    assert json_path == "out/20260625-101500/sector/sector.json"
    assert not any(path.is_dir() for path in output_dir.glob("20??????-??????*"))


def test_graph_imports_in_test_mode(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SECTOR_RESEARCH_TEST_MODE", "1")
    import sector_research_agent.graph as graph_module

    assert graph_module.graph == {
        "name": "sector_research",
        "test_mode": True,
        "backend_type": "filesystem",
    }
