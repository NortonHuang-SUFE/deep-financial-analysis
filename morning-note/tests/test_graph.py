from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class _CaptureToolsModel(BaseChatModel):
    captured: dict = {}

    def _respond(self, messages) -> ChatResult:
        self.captured["system_text"] = "\n".join(
            str(getattr(m, "content", ""))
            for m in messages
            if isinstance(m, SystemMessage)
        )
        msg = AIMessage(content="morning note complete")
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(self, messages, stop=None, run_manager=None, **kw) -> ChatResult:
        return self._respond(messages)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kw):
        return self._respond(messages)

    @property
    def _llm_type(self) -> str:
        return "capture-tools-model"

    def bind_tools(self, tools, **kw):
        self.captured["bound_tools"] = sorted(
            str(getattr(t, "name", getattr(t, "__name__", str(t)))) for t in tools
        )
        return self

    def _get_ls_params(self, stop=None, **kwargs):
        return {"ls_provider": "openai", "ls_model_name": "capture-tools-model"}


def test_morning_note_disables_general_purpose_task_tool(monkeypatch, tmp_path):
    monkeypatch.setenv("MORNING_NOTE_TEST_MODE", "1")
    from morning_note_agent import graph as morning_graph

    morning_graph = importlib.reload(morning_graph)
    monkeypatch.delenv("MORNING_NOTE_TEST_MODE", raising=False)

    model = _CaptureToolsModel(captured={})
    cfg = SimpleNamespace(output=SimpleNamespace(dir="./out"))

    async def _no_mcp_tools(_cfg):
        return []

    monkeypatch.setattr(morning_graph, "load_config", lambda: cfg)
    monkeypatch.setattr(morning_graph, "_build_model", lambda _cfg: model)
    monkeypatch.setattr(morning_graph, "_get_mcp_tools", _no_mcp_tools)
    monkeypatch.setattr(morning_graph, "file_storage_root", lambda: tmp_path)

    agent = asyncio.run(morning_graph._create_agent())
    asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "hi"}]}))

    assert "task" not in set(model.captured["bound_tools"])


def test_morning_note_prompt_forbids_general_purpose_subagent():
    prompt = (PROJECT_ROOT / "agents" / "morning-note.md").read_text(encoding="utf-8")
    skill = (PROJECT_ROOT / "skills" / "morning-note" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "禁止调用或请求 `general-purpose` subagent" in prompt
    assert "禁止调用或请求 `general-purpose` subagent" in skill
    assert "妙想 MX DS" in prompt
    assert "至少使用一次妙想" in prompt
    assert "妙想 MX DS" in skill


def test_morning_note_graph_uses_shared_general_purpose_disable_helper(monkeypatch):
    monkeypatch.setenv("MORNING_NOTE_TEST_MODE", "1")
    from morning_note_agent import graph as morning_graph

    source = inspect.getsource(morning_graph)

    assert "ensure_general_purpose_subagent_disabled(model)" in source
    assert "_HARNESS_PROFILES" not in source
    assert "harness_profiles" not in source
    assert "def _general_purpose_subagent_disabled" not in source


def test_morning_note_prompt_and_runtime_define_artifact_root():
    prompt = (PROJECT_ROOT / "agents" / "morning-note.md").read_text(encoding="utf-8")
    skill = (PROJECT_ROOT / "skills" / "morning-note" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "若 task 描述提供了上游产物根目录" in prompt
    assert "若 task 描述提供了上游产物根目录" in skill
    assert "不要再调用 `create_task_output_dir`" in skill

    from morning_note_agent import graph as morning_graph

    cfg = morning_graph.load_config()
    context = morning_graph._runtime_context_prompt(cfg)
    assert (
        "Artifact root: if the task description provides an output directory" in context
    )
    assert "do not create your own new top-level out/<timestamp>/ folder" in context


def test_morning_note_config_includes_mx_ds_mcp(monkeypatch, tmp_path):
    import financial_agent_runtime as runtime
    from morning_note_agent.config import enabled_mcp_server_configs, load_config

    for env_name in [
        "IFIND_MCP_TOKEN",
        "MX_DS_MCP_API_KEY",
        "MX_DS_MCP_URL",
        "MX_DS_MCP_TRANSPORT",
    ]:
        monkeypatch.delenv(env_name, raising=False)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
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
    assert server_configs["mx-ds-mcp"]["transport"] == "streamable_http"
    assert server_configs["mx-ds-mcp"]["headers"] == {"em_api_key": "mx-key"}
    assert cfg.mcp["mx-ds-mcp"].connect_timeout == 10
