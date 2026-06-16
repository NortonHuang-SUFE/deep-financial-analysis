"""Deep Orchestrator — LangGraph Deep Agents top-level graph.

The orchestrator registers the financial-analysis agents as **native Deep
Agents subagents**. It plans a request, then delegates to them with the
built-in `task` tool (parallel `task` calls run the subagents concurrently)
and writes its synthesis with shell-enabled built-in tools. There are no
custom invocation/IO tools — the Deep Agents runtime already provides them.

When the user wants a social card / 头图 / 小红书图文 / 公众号封面, the agent
follows the bundled `guizang-social-card-skill` under `skills/`.
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
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage, ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deep_orchestrator.config import (  # noqa: E402
    WORKSPACE_ROOT,
    file_storage_root,
    load_config,
)


# ── Native subagent registry ──────────────────────────────────────────────────
# name -> (folder, package, description). The description is what the parent
# model reads to decide when to delegate via the `task` tool.

_SUBAGENTS: dict[str, tuple[str, str, str]] = {
    "market_researcher": (
        "industry-ananlysis",
        "market_researcher",
        "Produce a sector or thematic market-research primer (markdown note, "
        "comps xlsx, optional Swiss-style PPTX deck). Delegate here for an "
        "industry overview, competitive landscape, or thematic idea list.",
    ),
    "morning_note": (
        "morning-note",
        "morning_note_agent",
        "Generate a Chinese pre-market A-share morning briefing "
        "(morning-note.md plus JSON artifacts). Delegate here for 早会纪要 / "
        "盘前 morning note / overnight summary / today's trade ideas.",
    ),
    "stock_screen": (
        "screen",
        "stock_screen_agent",
        "Screen China A-share and Hong Kong equities into a ranked investment "
        "shortlist (report.md + JSON). Delegate here for factor/style "
        "screening, idea generation, or building a watchlist.",
    ),
    "sector_research": (
        "sector",
        "sector_research_agent",
        "Investment-grade China sector / industry deep-dive aligned to "
        "Shenwan/CITIC/CNI taxonomies (report.md + JSON). Delegate here for "
        "行业研究 / 赛道分析 / value-chain mapping / policy analysis.",
    ),
    "thesis_tracker": (
        "thesis",
        "thesis_tracker_agent",
        "Create or update a falsifiable single-stock investment thesis "
        "(Chinese markdown scorecard + JSON). Delegate here to build, update, "
        "or review a thesis, or to get portfolio action advice.",
    ),
    "single_stock_coverage": (
        "single-stock-coverage",
        "single_stock_coverage_agent",
        "Complex single-stock coverage workflow under an outer research agent: "
        "initiating coverage, event updates, three-statement model, valuation "
        "assumption system, chart pack, and final report. Delegate here when "
        "one target company needs full coverage or post-event re-underwriting.",
    ),
}


# ── Tool error middleware (identical pattern to all sibling agents) ────────────


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


# ── Model builder (identical pattern to all sibling agents) ───────────────────


def _build_model(cfg):
    model_id = cfg.model.default
    if cfg.model.base_url:
        from langchain_openai import ChatOpenAI
        import httpx

        base_url = cfg.model.base_url.rstrip("/")
        parsed_base_url = urlparse(base_url)
        if not _is_allowed_model_gateway(parsed_base_url):
            raise ValueError(
                "model.base_url must be an HTTPS OpenAI-compatible gateway, "
                "or a local HTTP gateway on localhost/127.0.0.1."
            )
        if not cfg.model.api_key:
            raise ValueError(
                "Missing model API key. Set MODEL_GATEWAY_API_KEY, MODEL_API_KEY, "
                "DASHSCOPE_API_KEY, or model.api_key."
            )
        if not base_url.endswith("/v1"):
            base_url += "/v1"

        model_kwargs = dict(
            model=model_id,
            base_url=base_url,
            api_key=cfg.model.api_key,
            max_tokens=cfg.model.max_tokens,
            streaming=False,
            max_retries=3,
            timeout=300,  # orchestrator calls can take longer
        )

        proxy_url = (
            os.environ.get("https_proxy")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("http_proxy")
            or os.environ.get("HTTP_PROXY")
        )
        if proxy_url:
            model_kwargs["http_async_client"] = httpx.AsyncClient(
                proxy=proxy_url, verify=False
            )
            model_kwargs["http_client"] = httpx.Client(
                proxy=proxy_url, verify=False
            )

        return ChatOpenAI(**model_kwargs)

    model_kwargs: dict = {"max_tokens": cfg.model.max_tokens}
    if cfg.model.api_key:
        model_kwargs["api_key"] = cfg.model.api_key
    if ":" not in model_id:
        model_id = f"openai:{model_id}"
    from langchain.chat_models import init_chat_model

    return init_chat_model(model_id, **model_kwargs)


def _runtime_context_prompt() -> str:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    return (
        "\n\n## Runtime Context\n"
        f"Current Beijing time: {now:%Y-%m-%d %H:%M:%S %Z}.\n"
        f"Current Beijing date: {now:%Y-%m-%d}.\n"
        "When a user says today/tonight/this morning/now, expand it from "
        "this Beijing date/time. Include the concrete date/time in any "
        "subagent task description, especially for morning_note. Do not invent "
        "or reuse stale dates from examples or prior runs.\n"
    )


def _is_allowed_model_gateway(parsed_base_url) -> bool:
    host = parsed_base_url.hostname or ""
    if parsed_base_url.scheme == "https" and parsed_base_url.netloc:
        return True
    return parsed_base_url.scheme == "http" and host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


# ── Native subagent loading ───────────────────────────────────────────────────


def _load_subagent_runnable(folder: str, package: str):
    """Import a sibling agent package and return its compiled `graph`.

    Each sibling lives in its own src-layout package and builds its compiled
    graph either at import time or through a LangGraph-compatible factory
    function. We make its src/ importable, then import `<package>.graph` and
    hand back the compiled graph as a CompiledSubAgent runnable (its state
    schema already includes the required `messages` key).
    """
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
    specs: list[dict] = []
    for name, (folder, package, description) in _SUBAGENTS.items():
        specs.append(
            {
                "name": name,
                "description": description,
                "runnable": _load_subagent_runnable(folder, package),
            }
        )
    return specs


# ── Agent creation ────────────────────────────────────────────────────────────


def _create_agent():
    if os.getenv("ORCHESTRATOR_TEST_MODE") == "1":
        return {
            "name": "deep_orchestrator",
            "test_mode": True,
            "backend_type": "localshell",
        }

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend
    except ImportError as exc:
        raise ImportError(
            "deepagents is not installed. Run: pip install deepagents"
        ) from exc

    cfg = load_config()

    prompt_path = PROJECT_ROOT / "agents" / "orchestrator.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Agent prompt not found at {prompt_path}. Check the project files."
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    model = _build_model(cfg)
    subagents = _build_subagent_specs()
    backend = LocalShellBackend(
        root_dir=str(file_storage_root()),
        virtual_mode=False,
        inherit_env=True,
    )

    print(
        f"INFO: Deep Orchestrator — {len(subagents)} native subagents "
        f"({', '.join(s['name'] for s in subagents)}); no custom tools "
        "(built-in `task` + shell-enabled tools)."
    )

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[],
        subagents=subagents,
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=[
            _make_runtime_context_middleware(_runtime_context_prompt),
            _make_tool_error_middleware(),
        ],
        backend=backend,
        name="deep_orchestrator",
    )


# NOTE: `_create_agent` is synchronous on purpose. The orchestrator needs no
# MCP connections of its own (each subagent owns its MCP). Building it
# synchronously lets us import the sibling graphs — each of which calls
# `asyncio.run(...)` at import time — without nesting event loops.
try:
    graph = _create_agent()
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise deep_orchestrator agent: {exc}\n"
        "Check orchestrator/config.yaml, workspace .env, and installed packages."
    ) from exc
