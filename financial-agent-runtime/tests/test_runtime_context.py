"""Run-scoped runtime context middleware behaviour.

The provider caches on the request prefix, so the system message has to stay
byte-identical for the whole run. These tests pin that: one snapshot per graph
invocation, a fresh one for the next run, and no leakage between concurrent
runs.
"""

from __future__ import annotations

import asyncio
import itertools
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from financial_agent_runtime import (  # noqa: E402
    RUNTIME_CONTEXT_STATE_KEY,
    make_runtime_context_middleware,
)
from financial_agent_runtime.runtime_context import (  # noqa: E402
    _request_with_runtime_context,
)

from langchain_core.callbacks import CallbackManagerForLLMRun  # noqa: E402
from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import (  # noqa: E402
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402
from langchain_core.tools import tool  # noqa: E402


@tool
def ping(value: str) -> str:
    """Return a fixed acknowledgement so the agent takes another model turn."""
    return f"pong:{value}"


class RecordingChatModel(BaseChatModel):
    """Fake model that calls `ping` once, then answers.

    Responses are derived from the incoming messages rather than a shared
    iterator so two concurrent runs cannot consume each other's turns.
    """

    calls: list[tuple[str, str]] = []
    lock: Any = None

    @property
    def _llm_type(self) -> str:
        return "recording-fake"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "RecordingChatModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        system = next((m.text for m in messages if isinstance(m, SystemMessage)), "")
        marker = next((m.text for m in messages if isinstance(m, HumanMessage)), "")
        with self.lock:
            self.calls.append((marker, system))

        already_used_tool = any(isinstance(m, ToolMessage) for m in messages)
        if already_used_tool:
            message = AIMessage(content="done")
        else:
            message = AIMessage(
                content="",
                tool_calls=[{"name": "ping", "args": {"value": marker}, "id": "c1"}],
            )
        return ChatResult(generations=[ChatGeneration(message=message)])


def _build_agent(context_factory):
    from deepagents import create_deep_agent

    model = RecordingChatModel(calls=[], lock=threading.Lock())
    agent = create_deep_agent(
        model=model,
        system_prompt="base prompt",
        tools=[ping],
        middleware=[make_runtime_context_middleware(context_factory)],
    )
    return agent, model


def _counting_factory(prefix: str = "CTX"):
    counter = itertools.count()
    calls: list[str] = []

    def factory() -> str:
        # A short sleep widens the window in which two concurrent runs could
        # observe each other's snapshot if the value were not per-invocation.
        time.sleep(0.01)
        value = f"\n\n## Runtime Context\nsnapshot: {prefix}-{next(counter)}\n"
        calls.append(value)
        return value

    return factory, calls


def test_runtime_context_is_identical_for_every_call_in_one_run():
    factory, factory_calls = _counting_factory()
    agent, model = _build_agent(factory)

    result = agent.invoke({"messages": [HumanMessage("run-a")]})

    assert len(model.calls) >= 2, "the fake model should take a tool turn then answer"
    system_messages = {system for _marker, system in model.calls}
    assert len(system_messages) == 1, system_messages
    assert len(factory_calls) == 1
    assert factory_calls[0] in system_messages.pop()
    assert result[RUNTIME_CONTEXT_STATE_KEY] == factory_calls[0]


def test_each_run_computes_its_own_runtime_context():
    factory, factory_calls = _counting_factory()
    agent, model = _build_agent(factory)

    first = agent.invoke({"messages": [HumanMessage("run-a")]})
    second = agent.invoke({"messages": [HumanMessage("run-b")]})

    assert len(factory_calls) == 2
    assert first[RUNTIME_CONTEXT_STATE_KEY] != second[RUNTIME_CONTEXT_STATE_KEY]
    assert first[RUNTIME_CONTEXT_STATE_KEY] == factory_calls[0]
    assert second[RUNTIME_CONTEXT_STATE_KEY] == factory_calls[1]


def test_concurrent_runs_do_not_share_a_runtime_context():
    factory, factory_calls = _counting_factory()
    agent, model = _build_agent(factory)

    async def run_both():
        return await asyncio.gather(
            agent.ainvoke({"messages": [HumanMessage("run-a")]}),
            agent.ainvoke({"messages": [HumanMessage("run-b")]}),
        )

    first, second = asyncio.run(run_both())

    assert len(factory_calls) == 2
    assert first[RUNTIME_CONTEXT_STATE_KEY] != second[RUNTIME_CONTEXT_STATE_KEY]

    per_run: dict[str, set[str]] = {}
    for marker, system in model.calls:
        per_run.setdefault(marker, set()).add(system)
    assert set(per_run) == {"run-a", "run-b"}
    for marker, systems in per_run.items():
        assert len(systems) == 1, f"{marker} saw {len(systems)} different prompts"
    assert per_run["run-a"] != per_run["run-b"]


def test_runtime_context_falls_back_when_state_has_no_snapshot():
    factory, factory_calls = _counting_factory("FALLBACK")
    overrides: dict[str, Any] = {}

    class StubRequest:
        system_prompt = "base prompt"
        state: dict[str, Any] = {}

        def override(self, **kwargs: Any):
            overrides.update(kwargs)
            return self

    _request_with_runtime_context(StubRequest(), factory)

    assert len(factory_calls) == 1
    content = overrides["system_message"].text
    assert content.startswith("base prompt")
    assert factory_calls[0] in content


def test_existing_snapshot_wins_over_a_fresh_build():
    factory, factory_calls = _counting_factory()
    overrides: dict[str, Any] = {}

    class StubRequest:
        system_prompt = "base prompt"
        state = {RUNTIME_CONTEXT_STATE_KEY: "\n\nfrozen snapshot\n"}

        def override(self, **kwargs: Any):
            overrides.update(kwargs)
            return self

    _request_with_runtime_context(StubRequest(), factory)

    assert factory_calls == []
    assert overrides["system_message"].text == "base prompt\n\nfrozen snapshot\n"


def test_before_agent_keeps_a_snapshot_across_a_resumed_run():
    factory, factory_calls = _counting_factory()
    middleware = make_runtime_context_middleware(factory)

    created = middleware.before_agent({}, None)
    assert created is not None
    assert len(factory_calls) == 1

    resumed = middleware.before_agent(
        {RUNTIME_CONTEXT_STATE_KEY: created[RUNTIME_CONTEXT_STATE_KEY]}, None
    )
    assert resumed is None
    assert len(factory_calls) == 1


@pytest.mark.parametrize(
    "graph_path, package_src",
    [
        (
            PROJECT_ROOT.parent / "orchestrator" / "src" / "deep_orchestrator" / "graph.py",
            "orchestrator",
        ),
        (
            PROJECT_ROOT.parent
            / "morning-note"
            / "src"
            / "morning_note_agent"
            / "graph.py",
            "morning-note",
        ),
        (
            PROJECT_ROOT.parent
            / "html-image-renderer"
            / "src"
            / "html_image_renderer_agent"
            / "graph.py",
            "html-image-renderer",
        ),
    ],
)
def test_agent_graphs_use_the_shared_runtime_context_middleware(graph_path, package_src):
    source = graph_path.read_text(encoding="utf-8")

    assert "make_runtime_context_middleware" in source, package_src
    # A local copy would silently reintroduce the per-call clock this module
    # exists to remove.
    assert "_make_runtime_context_middleware" not in source, package_src
    assert "_request_with_runtime_context" not in source, package_src
