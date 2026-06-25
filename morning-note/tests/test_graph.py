from __future__ import annotations

import asyncio
import importlib
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
    prompt = (PROJECT_ROOT / "agents" / "morning-note.md").read_text(
        encoding="utf-8"
    )
    skill = (PROJECT_ROOT / "skills" / "morning-note" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "禁止调用或请求 `general-purpose` subagent" in prompt
    assert "禁止调用或请求 `general-purpose` subagent" in skill


def test_morning_note_prompt_and_runtime_define_artifact_root():
    prompt = (PROJECT_ROOT / "agents" / "morning-note.md").read_text(
        encoding="utf-8"
    )
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
        "Artifact root: if the task description provides an output directory"
        in context
    )
    assert "do not create your own new top-level out/<timestamp>/ folder" in context
