"""Tests for the Deep Orchestrator's native-subagent design.

These tests are hermetic — no model API key, no network, no MCP. They use a
fake tool-calling model and tiny compiled subagents to prove that:

1. The orchestrator delegates to subagents via the built-in `task` tool, and
   parallel `task` calls run the subagents *concurrently* (the headline
   requirement).
2. The agent is wired with the built-in Deep Agents tools only
   (`task` + filesystem + `write_todos`) and none of the old custom tools.
3. The bundled `guizang-social-card-skill` is discovered and offered to the
   model, while the deleted `orchestration` skill is gone.
4. The subagent registry is well-formed and matches the on-disk packages.

A separate, opt-in integration test (`ORCHESTRATOR_RUN_INTEGRATION=1`) builds
the real orchestrator graph end to end.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Annotated, TypedDict

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
SKILLS_DIR = PROJECT_ROOT / "skills"

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
_EXPECTED_BUILTIN_TOOLS = {"task", "write_file", "read_file", "ls", "write_todos"}


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
        self.captured["bound_tools"] = sorted(
            getattr(t, "name", getattr(t, "__name__", str(t))) for t in tools
        )
        return self


def _build_agent(model, subagents, *, with_skills: bool = False):
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend

    # Root the backend at the workspace, exactly like production, so the
    # SkillsMiddleware can read skills under orchestrator/skills/.
    backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=False)
    return create_deep_agent(
        model=model,
        tools=[],
        subagents=subagents,
        skills=[str(SKILLS_DIR)] if with_skills else None,
        backend=backend,
        name="orchestrator_under_test",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_subagent_registry_matches_disk():
    """The native registry lists the agents and their packages exist on disk."""
    os.environ["ORCHESTRATOR_TEST_MODE"] = "1"  # avoid building the heavy graph
    from deep_orchestrator import graph as orch

    expected = {
        "market_researcher",
        "morning_note",
        "stock_screen",
        "sector_research",
        "thesis_tracker",
        "single_stock_coverage",
    }
    assert set(orch._SUBAGENTS) == expected

    for name, (folder, package, description) in orch._SUBAGENTS.items():
        graph_file = WORKSPACE_ROOT / folder / "src" / package / "graph.py"
        assert graph_file.exists(), f"{name}: missing {graph_file}"
        assert description.strip(), f"{name}: empty description"


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


def test_social_card_skill_discovered_and_orchestration_skill_gone():
    """The guizang social-card skill is offered; the old orchestration skill is gone."""
    dummy, _ = _make_marker_subagent("single_stock_coverage", sleep_s=0.0)
    model = _ScriptedToolModel(tool_calls=[], captured={})
    agent = _build_agent(
        model,
        [{"name": "single_stock_coverage", "description": "d", "runnable": dummy}],
        with_skills=True,
    )
    asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "make a 头图"}]}))

    context = model.captured.get("context_text", "")
    assert "guizang-social-card-skill" in context
    # The deleted skill directory must not exist on disk either.
    assert not (SKILLS_DIR / "orchestration").exists()


@pytest.mark.skipif(
    os.getenv("ORCHESTRATOR_RUN_INTEGRATION") != "1",
    reason="set ORCHESTRATOR_RUN_INTEGRATION=1 to build the real graph (needs model key + sibling deps)",
)
def test_real_orchestrator_graph_builds():
    """Integration: the real orchestrator graph builds with 6 native subagents."""
    os.environ.pop("ORCHESTRATOR_TEST_MODE", None)
    import importlib

    import deep_orchestrator.graph as orch
    orch = importlib.reload(orch)
    assert orch.graph is not None
    # Compiled deep agents expose ainvoke.
    assert hasattr(orch.graph, "ainvoke")
