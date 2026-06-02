from pathlib import Path

from morning_note_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    load_config,
)
from morning_note_agent import tools


def test_default_config_resolves_from_project_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "morning-note"
    assert WORKSPACE_ROOT == PROJECT_ROOT.parent
    assert cfg.model.default == "qwen-3.7-max"
    assert cfg.model.base_url == "https://dashscope.aliyuncs.com/compatible-mode"
    assert cfg.output.dir == "./out"
    assert "ifind-stock" in cfg.mcp
    assert "ifind-fund" in cfg.mcp
    assert "ifind-global-stock" in cfg.mcp
    assert cfg.mcp["ifind-stock"].url


def test_workspace_env_and_process_env_override_ifind_auth(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    project = workspace / "morning-note"
    project.mkdir(parents=True)
    config_path = project / "config.yaml"
    config_path.write_text(
        """
model:
  default: yaml-model
  base_url: https://dashscope.aliyuncs.com/compatible-mode
mcp:
  ifind-stock:
    url: https://example.test/stock
    transport: streamable_http
  ifind-news:
    url: https://example.test/news
    transport: streamable_http
output:
  dir: ./out
""",
        encoding="utf-8",
    )
    workspace_env = workspace / ".env"
    workspace_env.write_text(
        """
IFIND_MCP_TOKEN=shared-token
MODEL_NAME=env-model
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("morning_note_agent.config.WORKSPACE_ENV_PATH", workspace_env)
    monkeypatch.setenv("IFIND_STOCK_MCP_AUTHORIZATION", "raw-stock-auth")

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert cfg.model.default == "env-model"
    assert cfg.mcp["ifind-stock"].headers["Authorization"] == "raw-stock-auth"
    assert cfg.mcp["ifind-news"].token == "shared-token"
    assert server_configs["ifind-news"]["headers"]["Authorization"] == "Bearer shared-token"


def test_timestamped_output_dir_is_workspace_relative(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_TIMESTAMP", "20260602-083000")

    out_dir = tools._timestamped_output_dir("./out")
    same_out_dir = tools._timestamped_output_dir("./out")
    explicit_dir = tools._timestamped_output_dir("./out/20260602-090000")

    assert out_dir == WORKSPACE_ROOT / "out" / "20260602-083000"
    assert out_dir.exists()
    assert same_out_dir == out_dir
    assert explicit_dir == WORKSPACE_ROOT / "out" / "20260602-090000"


def test_write_artifacts_share_timestamp(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_TIMESTAMP", "20260602-084500")

    markdown_path = tools.write_markdown_report.invoke(
        {"markdown": "# test", "filename": "早会.md", "output_dir": "./out"}
    )
    json_path = tools.write_json_artifact.invoke(
        {
            "data_json": '{"source": "ifind"}',
            "filename": "source-log.json",
            "output_dir": "./out",
        }
    )

    assert markdown_path == "out/20260602-084500/morning-note.md"
    assert json_path == "out/20260602-084500/source-log.json"
    assert (WORKSPACE_ROOT / markdown_path).exists()
    assert (WORKSPACE_ROOT / json_path).exists()

