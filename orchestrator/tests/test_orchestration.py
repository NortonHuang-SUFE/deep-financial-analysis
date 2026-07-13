"""Tests for the Daily Report coordinator graph."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, TypedDict

import pytest
import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_orchestrator.config import file_storage_root  # noqa: E402

_REMOVED_CUSTOM_TOOLS = {
    "invoke_subagent",
    "collect_subagent_outputs",
    "create_final_output_dir",
    "write_orchestration_summary",
    "write_orchestration_manifest",
    "prepare_social_card_content",
}

_EXPECTED_BUILTIN_TOOLS = {
    "task",
    "execute",
    "write_file",
    "read_file",
    "ls",
    "write_todos",
}

_REMOVED_CAPABILITY_TOKENS = {
    "DCF-builder",
    "dcf_builder",
    "dcf-assumption-researcher",
    "single-stock-coverage",
    "single_stock_coverage",
    "stock_screen",
    "sector_research",
    "thesis_tracker",
    "market_researcher",
    "industry-ananlysis",
    "screen",
    "sector",
    "thesis",
}


class _SubState(TypedDict):
    messages: Annotated[list, add_messages]


def _make_marker_subagent(name: str, sleep_s: float = 1.0):
    starts: dict[str, float] = {}

    async def _node(state: _SubState):
        starts["start"] = time.monotonic()
        await asyncio.sleep(sleep_s)
        return {"messages": [AIMessage(content=f"{name} finished")]}

    g = StateGraph(_SubState)
    g.add_node("run", _node)
    g.add_edge(START, "run")
    g.add_edge("run", END)
    return g.compile(), starts


class _ScriptedToolModel(BaseChatModel):
    tool_calls: list = []
    captured: dict = {}

    def _respond(self, messages) -> ChatResult:
        self.captured.setdefault("turns", 0)
        self.captured["turns"] += 1
        self.captured["context_text"] = "\n".join(
            str(getattr(m, "content", "")) for m in messages
        )
        self.captured["system_text"] = "\n".join(
            str(getattr(m, "content", "")) for m in messages
            if isinstance(m, SystemMessage)
        )
        if self.captured["turns"] == 1 and self.tool_calls:
            msg = AIMessage(
                content="",
                tool_calls=[
                    {"name": n, "args": a, "id": f"call_{i}"}
                    for i, (n, a) in enumerate(self.tool_calls)
                ],
            )
        else:
            msg = AIMessage(content="daily report complete")
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(self, messages, stop=None, run_manager=None, **kw) -> ChatResult:
        return self._respond(messages)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kw):
        return self._respond(messages)

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-model"

    def bind_tools(self, tools, **kw):
        tool_info = [_tool_info(t) for t in tools]
        self.captured["bound_tools"] = sorted(name for name, _ in tool_info)
        self.captured["tool_descriptions"] = dict(tool_info)
        return self

    def _get_ls_params(self, stop=None, **kwargs):
        return {"ls_provider": "openai", "ls_model_name": "scripted-tool-model"}


def _tool_info(tool) -> tuple[str, str]:
    if isinstance(tool, dict):
        function = tool.get("function") or {}
        name = tool.get("name") or function.get("name") or str(tool)
        description = tool.get("description") or function.get("description") or ""
        return str(name), str(description)
    name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
    description = getattr(tool, "description", "")
    return str(name), str(description)


def _build_agent(model, subagents):
    from deepagents import create_deep_agent
    from deepagents.backends import LocalShellBackend

    backend = LocalShellBackend(
        root_dir=str(file_storage_root()),
        virtual_mode=False,
        inherit_env=True,
    )
    return create_deep_agent(
        model=model,
        tools=[],
        subagents=subagents,
        skills=None,
        backend=backend,
        name="daily_report_under_test",
    )


def test_subagent_registry_matches_daily_report_surface(monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    expected = {"morning_note", "html_image_renderer"}
    assert set(orch._SUBAGENTS) == expected
    assert orch.graph["name"] == "daily_report"
    assert orch.graph["backend_type"] == "localshell"

    for name, (folder, package, description) in orch._SUBAGENTS.items():
        graph_file = WORKSPACE_ROOT / folder / "src" / package / "graph.py"
        assert graph_file.exists(), f"{name}: missing {graph_file}"
        assert description.strip(), f"{name}: empty description"


def test_loader_resolves_async_graph_factory(monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    class FakeRunnable:
        def with_config(self, _config):
            return self

    expected = FakeRunnable()

    async def graph_factory():
        return expected

    monkeypatch.setattr(
        orch.importlib,
        "import_module",
        lambda name: SimpleNamespace(graph=graph_factory),
    )

    assert orch._load_subagent_runnable("dummy-folder", "dummy_package") is expected


def test_runtime_context_prompt_includes_beijing_date_and_artifact_contract(monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    context = orch._runtime_context_prompt()

    assert "Current Beijing time:" in context
    assert "Current Beijing date:" in context
    assert "morning_note" in context
    assert "html_image_renderer" in context
    assert "<mother>/morning-note/" in context
    assert "<mother>/visual/<slot>/" in context
    assert "visual/pc/ and visual/mobile/" in context
    assert "never let two renderer tasks share an output_dir" in context
    assert "must not create their own new top-level" in context


def test_parallel_subagents_run_concurrently():
    sleep_s = 1.0
    note, note_starts = _make_marker_subagent("morning_note", sleep_s)
    visual, visual_starts = _make_marker_subagent("html_image_renderer", sleep_s)
    subagents = [
        {"name": "morning_note", "description": "Daily note", "runnable": note},
        {"name": "html_image_renderer", "description": "Visual", "runnable": visual},
    ]
    model = _ScriptedToolModel(
        tool_calls=[
            ("task", {"description": "write note", "subagent_type": "morning_note"}),
            (
                "task",
                {"description": "render visual", "subagent_type": "html_image_renderer"},
            ),
        ],
        captured={},
    )
    agent = _build_agent(model, subagents)

    t0 = time.monotonic()
    result = asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "go"}]}))
    wall = time.monotonic() - t0

    assert "start" in note_starts and "start" in visual_starts
    assert abs(note_starts["start"] - visual_starts["start"]) < 0.4
    assert wall < sleep_s * 1.8, f"expected concurrent (~{sleep_s}s), got {wall:.2f}s"

    texts = " ".join(str(getattr(m, "content", "")) for m in result["messages"])
    assert "morning_note finished" in texts
    assert "html_image_renderer finished" in texts


def test_builtin_tools_present_and_no_custom_tools():
    dummy, _ = _make_marker_subagent("morning_note", sleep_s=0.0)
    model = _ScriptedToolModel(tool_calls=[], captured={})
    agent = _build_agent(
        model,
        [{"name": "morning_note", "description": "d", "runnable": dummy}],
    )
    asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "hi"}]}))

    bound = set(model.captured.get("bound_tools", []))
    assert _EXPECTED_BUILTIN_TOOLS <= bound
    assert not (_REMOVED_CUSTOM_TOOLS & bound)


def test_daily_report_task_tool_excludes_general_purpose(monkeypatch, tmp_path):
    monkeypatch.setenv("DAILY_REPORT_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    monkeypatch.delenv("DAILY_REPORT_TEST_MODE", raising=False)
    dummy, _ = _make_marker_subagent("morning_note", sleep_s=0.0)
    model = _ScriptedToolModel(
        tool_calls=[
            (
                "task",
                {
                    "description": "try the disabled generic route",
                    "subagent_type": "general-purpose",
                },
            )
        ],
        captured={},
    )

    monkeypatch.setattr(
        orch,
        "build_chat_model_for_agent",
        lambda _workspace_root, _agent_name, timeout=300: model,
    )
    monkeypatch.setattr(
        orch,
        "_build_subagent_specs",
        lambda: [{"name": "morning_note", "description": "d", "runnable": dummy}],
    )
    monkeypatch.setattr(orch, "file_storage_root", lambda: tmp_path)

    agent = orch._create_agent()
    result = asyncio.run(
        agent.ainvoke({"messages": [{"role": "user", "content": "hi"}]})
    )

    task_description = model.captured["tool_descriptions"]["task"]
    assert "morning_note" in task_description
    texts = " ".join(str(getattr(m, "content", "")) for m in result["messages"])
    assert "We cannot invoke subagent general-purpose" in texts
    assert "only allowed types are `morning_note`" in texts


def test_daily_report_does_not_mount_orchestrator_skills(monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    source = inspect.getsource(orch._create_agent)
    assert "skills=None" in source
    assert "PROJECT_ROOT / \"skills\"" not in source

    dummy, _ = _make_marker_subagent("html_image_renderer", sleep_s=0.0)
    model = _ScriptedToolModel(tool_calls=[], captured={})
    agent = _build_agent(
        model,
        [{"name": "html_image_renderer", "description": "d", "runnable": dummy}],
    )
    asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "make a 头图"}]}))

    context = model.captured.get("context_text", "")
    assert "guizang-social-card-skill" not in context


def test_prompt_routes_daily_report_and_images_only():
    prompt = (PROJECT_ROOT / "agents" / "orchestrator.md").read_text(encoding="utf-8")

    assert "daily_report" in prompt
    assert "morning_note" in prompt
    assert "html_image_renderer" in prompt
    assert "source_paths" in prompt
    assert "Never paste entire Markdown/CSV/JSON" in prompt
    assert "all artifact paths" in prompt
    assert "complete artifact index" in prompt
    assert "every absolute path produced or received" in prompt
    assert "所有产物地址" in prompt
    assert "pre-assign one exclusive visual slot directory" in prompt
    assert "<mother>/visual/pc/" in prompt
    assert "<mother>/visual/mobile/" in prompt
    assert "Never assign the same `output_dir` to two renderer task calls" in prompt
    assert "no returned path is duplicated across image variants" in prompt
    assert "must never" not in prompt.lower()
    assert "general-purpose" in prompt

    for token in _REMOVED_CAPABILITY_TOKENS:
        assert token not in prompt


def test_graph_uses_shared_general_purpose_disable_helper(monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    source = inspect.getsource(orch)

    assert "ensure_general_purpose_subagent_disabled(model)" in source
    assert "_HARNESS_PROFILES" not in source
    assert "harness_profiles" not in source


def test_root_langgraph_exposes_only_daily_report():
    config = json.loads((WORKSPACE_ROOT / "langgraph.json").read_text(encoding="utf-8"))

    assert set(config["graphs"]) == {"daily_report"}
    assert config["graphs"]["daily_report"] == (
        "./orchestrator/src/deep_orchestrator/graph.py:graph"
    )
    assert config["dependencies"] == [
        "./financial-agent-runtime",
        "./morning-note",
        "./orchestrator",
        "./html-image-renderer",
    ]
    assert any("chromium" in line for line in config["dockerfile_lines"])
    assert "ADD ./model-routing.yaml /deps/model-routing.yaml" in config[
        "dockerfile_lines"
    ]
    assert "ADD ./tool-concurrency.yaml /deps/tool-concurrency.yaml" in config[
        "dockerfile_lines"
    ]


def test_root_configs_remove_deleted_research_capabilities():
    routing = yaml.safe_load((WORKSPACE_ROOT / "model-routing.yaml").read_text())
    tools = yaml.safe_load((WORKSPACE_ROOT / "tool-concurrency.yaml").read_text())
    langgraph = json.loads((WORKSPACE_ROOT / "langgraph.json").read_text())

    config_text = "\n".join(
        [
            json.dumps(langgraph, sort_keys=True),
            yaml.safe_dump(routing, sort_keys=True),
            yaml.safe_dump(tools, sort_keys=True),
        ]
    )

    assert set(routing["agent_models"]) == {
        "daily_report",
        "morning_note",
        "html_image_renderer",
    }
    assert set(tools["agent_configs"]) == {
        "daily_report",
        "morning_note",
        "html_image_renderer",
    }
    assert set(tools["agent_tools"]) == {"morning_note"}
    for token in _REMOVED_CAPABILITY_TOKENS:
        assert token not in config_text


@pytest.mark.skipif(
    os.getenv("ORCHESTRATOR_RUN_INTEGRATION") != "1",
    reason="set ORCHESTRATOR_RUN_INTEGRATION=1 to build the real graph (needs model key + sibling deps)",
)
def test_real_daily_report_graph_builds(monkeypatch):
    monkeypatch.delenv("DAILY_REPORT_TEST_MODE", raising=False)
    import importlib

    import deep_orchestrator.graph as orch

    orch = importlib.reload(orch)
    assert orch.graph is not None
    assert hasattr(orch.graph, "ainvoke")
