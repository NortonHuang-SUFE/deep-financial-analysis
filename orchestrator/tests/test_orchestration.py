"""Tests for the Deep Orchestrator's native-subagent design.

These tests are hermetic — no model API key, no network, no MCP. They use a
fake tool-calling model and tiny compiled subagents to prove that:

1. The orchestrator delegates to subagents via the built-in `task` tool, and
   parallel `task` calls run the subagents *concurrently* (the headline
   requirement).
2. The agent is wired with the built-in Deep Agents tools only
   (`task` + shell-enabled built-in tools + `write_todos`) and none of the old
   custom tools.
3. Visual/image requests are routed to the `html_image_renderer` subagent with
   artifact paths, and the orchestrator no longer mounts its own skills.
4. The subagent registry is well-formed and matches the on-disk packages.

A separate, opt-in integration test (`ORCHESTRATOR_RUN_INTEGRATION=1`) builds
the real orchestrator graph end to end.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, TypedDict

import pytest
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

# Old custom tools that must no longer be registered on the orchestrator.
_REMOVED_CUSTOM_TOOLS = {
    "invoke_subagent",
    "collect_subagent_outputs",
    "create_final_output_dir",
    "write_orchestration_summary",
    "write_orchestration_manifest",
    "prepare_social_card_content",
}

# Built-in Deep Agents tools we expect the orchestrator to rely on instead.
_EXPECTED_BUILTIN_TOOLS = {
    "task",
    "execute",
    "write_file",
    "read_file",
    "ls",
    "write_todos",
}


# ── Test doubles ──────────────────────────────────────────────────────────────


class _SubState(TypedDict):
    messages: Annotated[list, add_messages]


def _make_marker_subagent(name: str, sleep_s: float = 1.0):
    """A tiny compiled subagent that records its start time, then sleeps.

    Recording the start time lets the parallel test assert overlap rather than
    only total wall-clock time.
    """
    starts: dict[str, float] = {}

    async def _node(state: _SubState):
        starts["start"] = time.monotonic()
        await asyncio.sleep(sleep_s)
        return {"messages": [AIMessage(content=f"{name} finished")]}

    g = StateGraph(_SubState)
    g.add_node("run", _node)
    g.add_edge(START, "run")
    g.add_edge("run", END)
    compiled = g.compile()
    return compiled, starts


class _ScriptedToolModel(BaseChatModel):
    """A fake model: first turn emits a fixed set of tool calls, then stops.

    `tool_calls` is the list of (name, args) the first AI turn should request.
    On every subsequent turn it returns a plain final message. It also captures
    the tool names it was bound with and the full text it was shown.
    """

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
            msg = AIMessage(content="orchestration complete")
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

    # Root the backend at the shared storage root, exactly like production.
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
        name="orchestrator_under_test",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_subagent_registry_matches_disk(monkeypatch):
    """The native registry lists the agents and their packages exist on disk."""
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")  # avoid building the heavy graph
    from deep_orchestrator import graph as orch

    expected = {
        "market_researcher",
        "morning_note",
        "stock_screen",
        "sector_research",
        "thesis_tracker",
        "single_stock_coverage",
        "html_image_renderer",
    }
    assert set(orch._SUBAGENTS) == expected
    assert orch.graph["backend_type"] == "localshell"

    for name, (folder, package, description) in orch._SUBAGENTS.items():
        graph_file = WORKSPACE_ROOT / folder / "src" / package / "graph.py"
        assert graph_file.exists(), f"{name}: missing {graph_file}"
        assert description.strip(), f"{name}: empty description"


def test_loader_resolves_async_graph_factory(monkeypatch):
    """Sibling agents may expose `graph` as an async LangGraph factory."""
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")  # avoid building the heavy graph
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


def test_runtime_context_prompt_includes_beijing_time(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    context = orch._runtime_context_prompt()

    assert "Current Beijing time:" in context
    assert "Current Beijing date:" in context
    assert "morning_note" in context
    assert "Do not invent" in context


def test_parallel_subagents_run_concurrently():
    """Two `task` calls in one turn must run their subagents in parallel."""
    sleep_s = 1.0
    alpha, alpha_starts = _make_marker_subagent("alpha", sleep_s)
    beta, beta_starts = _make_marker_subagent("beta", sleep_s)
    subagents = [
        {"name": "alpha", "description": "Independent task A", "runnable": alpha},
        {"name": "beta", "description": "Independent task B", "runnable": beta},
    ]
    model = _ScriptedToolModel(
        tool_calls=[
            ("task", {"description": "do A", "subagent_type": "alpha"}),
            ("task", {"description": "do B", "subagent_type": "beta"}),
        ],
        captured={},
    )
    agent = _build_agent(model, subagents)

    t0 = time.monotonic()
    result = asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "go"}]}))
    wall = time.monotonic() - t0

    # Both subagents actually ran.
    assert "start" in alpha_starts and "start" in beta_starts
    # They started within a small window of each other → concurrent, not serial.
    assert abs(alpha_starts["start"] - beta_starts["start"]) < 0.4
    # Wall clock is ~one sleep, not two.
    assert wall < sleep_s * 1.8, f"expected concurrent (~{sleep_s}s), got {wall:.2f}s"

    texts = " ".join(str(getattr(m, "content", "")) for m in result["messages"])
    assert "alpha finished" in texts and "beta finished" in texts


def test_builtin_tools_present_and_no_custom_tools():
    """The orchestrator exposes built-in tools and none of the old custom ones."""
    dummy, _ = _make_marker_subagent("single_stock_coverage", sleep_s=0.0)
    model = _ScriptedToolModel(tool_calls=[], captured={})
    agent = _build_agent(
        model, [{"name": "single_stock_coverage", "description": "d", "runnable": dummy}]
    )
    asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "hi"}]}))

    bound = set(model.captured.get("bound_tools", []))
    assert _EXPECTED_BUILTIN_TOOLS <= bound, f"missing built-ins: {_EXPECTED_BUILTIN_TOOLS - bound}"
    leaked = _REMOVED_CUSTOM_TOOLS & bound
    assert not leaked, f"removed custom tools still present: {leaked}"


def test_orchestrator_task_tool_excludes_general_purpose(monkeypatch, tmp_path):
    """The top-level task tool must reject the auto-added GP subagent."""
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    monkeypatch.delenv("ORCHESTRATOR_TEST_MODE", raising=False)
    dummy, _ = _make_marker_subagent("market_researcher", sleep_s=0.0)
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
        lambda: [{"name": "market_researcher", "description": "d", "runnable": dummy}],
    )
    monkeypatch.setattr(orch, "file_storage_root", lambda: tmp_path)

    agent = orch._create_agent()
    result = asyncio.run(
        agent.ainvoke({"messages": [{"role": "user", "content": "hi"}]})
    )

    task_description = model.captured["tool_descriptions"]["task"]
    assert "market_researcher" in task_description
    texts = " ".join(str(getattr(m, "content", "")) for m in result["messages"])
    assert "We cannot invoke subagent general-purpose" in texts
    assert "only allowed types are `market_researcher`" in texts


def test_orchestrator_does_not_mount_skills(monkeypatch):
    """Production orchestrator delegates visual work instead of loading skills."""
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")
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


def test_orchestrator_prompt_routes_images_by_artifact_paths():
    """Visual requests must pass artifact file paths to html_image_renderer."""
    prompt = (PROJECT_ROOT / "agents" / "orchestrator.md").read_text(encoding="utf-8")

    assert "html_image_renderer" in prompt
    assert "source_paths" in prompt
    assert "file addresses" in prompt
    assert "not full file contents" in prompt
    assert "Never paste an entire upstream Markdown/CSV" in prompt
    assert "guizang-social-card-skill" not in prompt


def test_orchestrator_prompt_forbids_general_purpose_subagent():
    prompt = (PROJECT_ROOT / "agents" / "orchestrator.md").read_text(encoding="utf-8")

    assert "must never call or request a `general-purpose` subagent" in prompt
    assert "only valid synchronous `task.subagent_type` values" in prompt


def test_orchestrator_graph_uses_shared_general_purpose_disable_helper(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    source = inspect.getsource(orch)

    assert "ensure_general_purpose_subagent_disabled(model)" in source
    assert "_HARNESS_PROFILES" not in source
    assert "harness_profiles" not in source
    assert "def _general_purpose_subagent_disabled" not in source


def test_orchestrator_prompt_defines_single_artifact_root():
    prompt = (PROJECT_ROOT / "agents" / "orchestrator.md").read_text(encoding="utf-8")

    assert "Artifact root" in prompt
    assert "single mother folder" in prompt
    assert "Fix one mother folder at the start of the run" in prompt
    assert "`<mother>/<subdir>/`" in prompt
    assert "to create its own new top-level `out/<timestamp>/` folder" in prompt


def test_runtime_context_prompt_defines_artifact_root(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")
    from deep_orchestrator import graph as orch

    context = orch._runtime_context_prompt()

    assert "Artifact base directory:" in context
    assert "Fix ONE mother folder for this whole run" in context
    assert "<mother>/<subdir>/" in context
    assert "must not create their own new top-level" in context


@pytest.mark.skipif(
    os.getenv("ORCHESTRATOR_RUN_INTEGRATION") != "1",
    reason="set ORCHESTRATOR_RUN_INTEGRATION=1 to build the real graph (needs model key + sibling deps)",
)
def test_real_orchestrator_graph_builds(monkeypatch):
    """Integration: the real orchestrator graph builds with native subagents."""
    monkeypatch.delenv("ORCHESTRATOR_TEST_MODE", raising=False)
    import importlib

    import deep_orchestrator.graph as orch
    orch = importlib.reload(orch)
    assert orch.graph is not None
    # Compiled deep agents expose ainvoke.
    assert hasattr(orch.graph, "ainvoke")
