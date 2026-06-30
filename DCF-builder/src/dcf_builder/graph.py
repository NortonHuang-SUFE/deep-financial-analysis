"""DCF Builder - LangGraph Deep Agents graph."""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import ToolMessage

# LangGraph loads this file by path, so make the src-layout package importable
# before importing dcf_builder.* modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dcf_builder.assumption_research import (
    ASSUMPTION_MCP_SERVER_NAMES,
    create_assumption_research_subagent_spec,
)
from financial_agent_runtime import (
    load_and_register_mcp_tools,
    make_concurrency_limit_middleware,
    normalize_openai_compatible_base_url,
)

from dcf_builder.config import (
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    build_backend,
    mirror_skills_into_backend,
    load_config,
)
from dcf_builder.tools import (
    build_comps_excel,
    build_dcf_model,
    validate_dcf_model,
    write_assumption_analysis,
    write_valuation_summary,
)


def _make_tool_error_middleware():
    """Catch tool errors and return them to the model for recovery."""
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


async def _load_mcp_tools_from_config(server_configs: dict) -> list:
    return await load_and_register_mcp_tools(
        server_configs, workspace_root=WORKSPACE_ROOT
    )


def _get_search_tools(cfg):
    provider = cfg.search.provider
    if provider == "none" or not provider:
        return []

    if provider == "tavily":
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            api_key = cfg.search.api_key or os.getenv("TAVILY_API_KEY") or ""
            if api_key:
                os.environ.setdefault("TAVILY_API_KEY", api_key)
            return [TavilySearchResults(max_results=cfg.search.max_results)]
        except ImportError:
            print("WARNING: tavily-python not installed. Search disabled.")
            return []

    if provider == "duckduckgo":
        try:
            from langchain_community.tools import DuckDuckGoSearchResults

            return [DuckDuckGoSearchResults(max_results=cfg.search.max_results)]
        except ImportError:
            print("WARNING: duckduckgo-search not installed. Search disabled.")
            return []

    if provider == "serper":
        try:
            from langchain_community.utilities import GoogleSerperAPIWrapper
            from langchain_core.tools import Tool

            api_key = cfg.search.api_key or os.getenv("SERPER_API_KEY") or ""
            if api_key:
                os.environ.setdefault("SERPER_API_KEY", api_key)
            wrapper = GoogleSerperAPIWrapper()
            return [
                Tool(
                    name="web_search",
                    func=wrapper.run,
                    description="Fallback search for public financial sources.",
                )
            ]
        except ImportError:
            print("WARNING: google-search-results not installed. Search disabled.")
            return []

    print(f"WARNING: Unknown search provider '{provider}'. Search disabled.")
    return []


async def _get_mcp_tools(cfg, server_names: Sequence[str] | None = None) -> list:
    server_configs = enabled_mcp_server_configs(cfg)
    if server_names is not None:
        allowed = set(server_names)
        server_configs = {
            name: server_config
            for name, server_config in server_configs.items()
            if name in allowed
        }
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(f"INFO: Loaded {len(tools)} MCP tool(s) from: {list(server_configs)}")
    return tools


def _build_model(cfg):
    model_id = cfg.model.default
    if cfg.model.base_url:
        from langchain_openai import ChatOpenAI
        import httpx

        base_url = normalize_openai_compatible_base_url(cfg.model.base_url)
        parsed_base_url = urlparse(base_url)
        if not _is_allowed_model_gateway(parsed_base_url):
            raise ValueError(
                "model.base_url must be an HTTPS OpenAI-compatible gateway, "
                "or a local HTTP gateway on localhost/127.0.0.1."
            )
        if not cfg.model.api_key:
            raise ValueError(
                "Missing model API key. Set MODEL_GATEWAY_API_KEY, MODEL_API_KEY, "
                "a provider-specific key such as DASHSCOPE_API_KEY or ARK_API_KEY, "
                "or model.api_key."
            )
        model_kwargs = dict(
            model=model_id,
            base_url=base_url,
            api_key=cfg.model.api_key,
            max_tokens=cfg.model.max_tokens,
            streaming=False,
            max_retries=3,
            timeout=120,
        )
        if parsed_base_url.netloc.lower() == "api.deepseek.com":
            thinking = cfg.model.thinking
            if thinking == "auto" and model_id.startswith("deepseek-v4"):
                thinking = "disabled"
            if thinking in {"enabled", "disabled"}:
                model_kwargs["extra_body"] = {"thinking": {"type": thinking}}

        proxy_url = (
            os.environ.get("https_proxy")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("http_proxy")
            or os.environ.get("HTTP_PROXY")
        )
        if proxy_url:
            model_kwargs["http_async_client"] = httpx.AsyncClient(proxy=proxy_url, verify=False)
            model_kwargs["http_client"] = httpx.Client(proxy=proxy_url, verify=False)

        return ChatOpenAI(**model_kwargs)

    model_kwargs: dict = {"max_tokens": cfg.model.max_tokens}
    if cfg.model.api_key:
        model_kwargs["api_key"] = cfg.model.api_key
    if ":" not in model_id:
        model_id = f"openai:{model_id}"
    from langchain.chat_models import init_chat_model

    return init_chat_model(model_id, **model_kwargs)


def _is_allowed_model_gateway(parsed_base_url) -> bool:
    host = parsed_base_url.hostname or ""
    if parsed_base_url.scheme == "https" and parsed_base_url.netloc:
        return True
    return parsed_base_url.scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}


async def _create_agent():
    if os.getenv("DCF_BUILDER_TEST_MODE") == "1":
        return {
            "name": "dcf_builder",
            "test_mode": True,
            "backend_type": "localshell",
        }

    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()

    prompt_path = PROJECT_ROOT / "agents" / "dcf-builder.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Agent prompt not found at {prompt_path}. Check the project files."
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    model = _build_model(cfg)
    mcp_tools = await _get_mcp_tools(cfg)
    assumption_mcp_tools = await _get_mcp_tools(cfg, ASSUMPTION_MCP_SERVER_NAMES)
    search_tools = _get_search_tools(cfg)
    local_tools = [
        build_comps_excel,
        build_dcf_model,
        validate_dcf_model,
        write_valuation_summary,
    ]
    backend = build_backend(prefer_shell=True)
    assumption_tools = assumption_mcp_tools + search_tools + [write_assumption_analysis]
    assumption_subagent = create_assumption_research_subagent_spec(
        model=model,
        tools=assumption_tools,
        middleware=[
            make_concurrency_limit_middleware(WORKSPACE_ROOT),
            _make_tool_error_middleware(),
        ],
        backend=backend,
    )

    all_tools = mcp_tools + search_tools + local_tools
    print(
        f"INFO: Agent tools - MCP: {len(mcp_tools)}, "
        f"Search: {len(search_tools)}, Local: {len(local_tools)}, "
        f"Assumption subagent MCP: {len(assumption_mcp_tools)}"
    )

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=all_tools,
        subagents=[assumption_subagent],
        skills=[mirror_skills_into_backend(backend, PROJECT_ROOT / "skills")],
        middleware=[
            make_concurrency_limit_middleware(WORKSPACE_ROOT),
            _make_tool_error_middleware(),
        ],
        backend=backend,
        name="dcf_builder",
    )


try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise dcf_builder agent: {exc}\n"
        "Check config.yaml, .env, and installed packages."
    ) from exc
