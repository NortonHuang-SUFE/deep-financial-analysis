"""Daily Report coordinator graph.

The public LangGraph assistant is `daily_report`. It coordinates exactly two
native Deep Agents subagents:

* `morning_note` writes the China-market daily note artifacts.
* `html_image_renderer` turns existing artifacts into one HTML-rendered PNG.
"""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import importlib
import inspect
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage, ToolMessage

from financial_agent_runtime import (
    build_chat_model_for_agent,
    ensure_general_purpose_subagent_disabled,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_orchestrator.config import (  # noqa: E402
    WORKSPACE_ROOT,
    build_backend,
    file_storage_root,
)


_SUBAGENTS: dict[str, tuple[str, str, str]] = {
    "morning_note": (
        "morning-note",
        "morning_note_agent",
        "Generate a Chinese pre-market A-share daily report / morning note "
        "(morning-note.md plus JSON source artifacts). Delegate here for 日报, "
        "早会纪要, 盘前 morning note, overnight summary, or today's trade ideas.",
    ),
    "html_image_renderer": (
        "html-image-renderer",
        "html_image_renderer_agent",
        "Read existing artifact files and render exactly one HTML-based PNG. "
        "Delegate here for a 头图, daily-report cover image, social-style visual, "
        "or image from markdown/csv/json source artifacts. Pass artifact file paths, "
        "not pasted contents.",
    ),
}

AGENT_NAME = "daily_report"


def _make_runtime_context_middleware(context_factory):
    """Append fresh runtime context to every model call."""
    from deepagents.middleware.skills import SkillsMiddleware

    AgentMiddleware = SkillsMiddleware.__mro__[1]

    class RuntimeContextMiddleware(AgentMiddleware):
        tools = []

        def wrap_model_call(self, request, handler):
            return handler(_request_with_runtime_context(request, context_factory()))

        async def awrap_model_call(self, request, handler):
            return await handler(_request_with_runtime_context(request, context_factory()))

    return RuntimeContextMiddleware()


def _request_with_runtime_context(request, runtime_context: str):
    base_prompt = request.system_prompt or ""
    return request.override(
        system_message=SystemMessage(content=base_prompt + runtime_context)
    )


def _make_tool_error_middleware():
    """Catch tool errors and return them to the model for self-recovery."""
    from deepagents.middleware.skills import SkillsMiddleware

    AgentMiddleware = SkillsMiddleware.__mro__[1]

    class ToolErrorHandlerMiddleware(AgentMiddleware):
        tools = []

        def wrap_tool_call(self, request, handler):
            try:
                return handler(request)
            except Exception as exc:
                return _tool_error_message(request, exc)

        async def awrap_tool_call(self, request, handler):
            try:
                return await handler(request)
            except Exception as exc:
                return _tool_error_message(request, exc)

    return ToolErrorHandlerMiddleware()


def _tool_error_message(request, exc: Exception) -> ToolMessage:
    name = request.tool_call.get("name", "unknown")
    return ToolMessage(
        content=(
            f"Error executing tool '{name}': {type(exc).__name__}: {exc}\n"
            "Please adjust your parameters and try again."
        ),
        name=name,
        tool_call_id=request.tool_call.get("id", ""),
        status="error",
    )


def _runtime_context_prompt() -> str:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    artifact_base = file_storage_root() / "out"
    return (
        "\n\n## Runtime Context\n"
        f"Current Beijing time: {now:%Y-%m-%d %H:%M:%S %Z}.\n"
        f"Current Beijing date: {now:%Y-%m-%d}.\n"
        "When a user says today/tonight/this morning/now, expand it from this "
        "Beijing date/time. Include the concrete date/time in every "
        "`morning_note` task description. Do not invent or reuse stale dates "
        "from examples or prior runs.\n"
        f"Artifact base directory: {artifact_base}.\n"
        "Fix ONE mother folder for this daily-report run: "
        f"{artifact_base}/<YYYYMMDD-HHMMSS>/. Choose it once on your first "
        "delegation and reuse the identical path later. Pass "
        "<mother>/morning-note/ to `morning_note` and <mother>/visual/ to "
        "`html_image_renderer` when rendering is requested. Subagents must not "
        "create their own new top-level out/<timestamp>/ folder. Write your own "
        "daily-report summary into the same mother folder.\n"
    )


def _load_subagent_runnable(folder: str, package: str):
    """Import a sibling src-layout package and return its compiled graph."""
    src_path = str(WORKSPACE_ROOT / folder / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    mod = importlib.import_module(f"{package}.graph")
    graph = mod.graph
    if inspect.isfunction(graph) or inspect.ismethod(graph):
        graph = graph()
    if inspect.isawaitable(graph):
        graph = asyncio.run(graph)
    if not hasattr(graph, "with_config"):
        raise TypeError(
            f"{package}.graph:graph resolved to {type(graph).__name__}, "
            "expected a LangGraph/LangChain runnable with .with_config()."
        )
    return graph


def _build_subagent_specs() -> list[dict]:
    return [
        {
            "name": name,
            "description": description,
            "runnable": _load_subagent_runnable(folder, package),
        }
        for name, (folder, package, description) in _SUBAGENTS.items()
    ]


def _test_mode_enabled() -> bool:
    return (
        os.getenv("DAILY_REPORT_TEST_MODE") == "1"
        or os.getenv("ORCHESTRATOR_TEST_MODE") == "1"
    )


def _create_agent():
    if _test_mode_enabled():
        return {
            "name": AGENT_NAME,
            "test_mode": True,
            "backend_type": "localshell",
        }

    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise ImportError(
            "deepagents is not installed. Run: pip install deepagents"
        ) from exc

    prompt_path = PROJECT_ROOT / "agents" / "orchestrator.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Agent prompt not found at {prompt_path}. Check the project files."
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    model = build_chat_model_for_agent(WORKSPACE_ROOT, AGENT_NAME, timeout=300)
    subagents = _build_subagent_specs()
    backend = build_backend(prefer_shell=True)

    print(
        f"INFO: Daily Report coordinator — {len(subagents)} native subagents "
        f"({', '.join(s['name'] for s in subagents)}); no custom tools "
        "(built-in `task` + shell-enabled tools)."
    )

    ensure_general_purpose_subagent_disabled(model)
    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[],
        subagents=subagents,
        skills=None,
        middleware=[
            _make_runtime_context_middleware(_runtime_context_prompt),
            _make_tool_error_middleware(),
        ],
        backend=backend,
        name=AGENT_NAME,
    )


try:
    graph = _create_agent()
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise daily_report agent: {exc}\n"
        "Check root tool-concurrency.yaml, model-routing.yaml, .env, and installed packages."
    ) from exc
