"""Market Researcher — LangGraph Deep Agents graph.

This module builds the agent using deepagents.create_deep_agent() and
exposes a `graph` object that langgraph.json points to.

Skills in ./skills/ are auto-discovered by deepagents.
MCP tools are loaded from the workspace root tool-concurrency.yaml at startup.
Search tools are selected by the configured provider.
Local tools (build_comps_excel, build_pptx) are always available.
"""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import ToolMessage

# LangGraph loads this file by path, so make the src-layout package importable
# before importing market_researcher.* modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from financial_agent_runtime import (
    build_chat_model_for_agent,
    build_tool_catalog,
    load_and_register_mcp_tools,
    load_tool_access_config,
    make_concurrency_limit_middleware,
    mcp_server_names_for_tool_group,
    mcp_tool_group_names_for_agent,
    resolve_agent_tools,
)

from market_researcher.config import (
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    build_backend,
    mirror_skills_into_backend,
    ifind_auth_headers,
    load_config,
)
from market_researcher.tools import build_comps_excel, build_pptx

AGENT_NAME = "market_researcher"


# ── Tool error handling middleware ────────────────────────────────────────────

def _make_tool_error_middleware():
    """Create a middleware that catches tool errors and returns them to the model."""
    from deepagents.middleware.skills import SkillsMiddleware
    AgentMiddleware = SkillsMiddleware.__mro__[1]  # Get AgentMiddleware base class

    class ToolErrorHandlerMiddleware(AgentMiddleware):
        """Catch all tool call exceptions and return error messages to the model,
        so the agent can retry or adjust instead of crashing."""

        tools = []  # No extra tools

        def wrap_tool_call(self, request, handler):
            try:
                return handler(request)
            except Exception as e:
                error_msg = (
                    f"Error executing tool '{request.tool_call.get('name', '?')}': "
                    f"{type(e).__name__}: {e}\n"
                    f"Please adjust your parameters and try again."
                )
                print(f"WARNING [ToolErrorHandler]: {error_msg}")
                return ToolMessage(
                    content=error_msg,
                    name=request.tool_call.get("name", "unknown"),
                    tool_call_id=request.tool_call.get("id", ""),
                    status="error",
                )

        async def awrap_tool_call(self, request, handler):
            try:
                return await handler(request)
            except Exception as e:
                error_msg = (
                    f"Error executing tool '{request.tool_call.get('name', '?')}': "
                    f"{type(e).__name__}: {e}\n"
                    f"Please adjust your parameters and try again."
                )
                print(f"WARNING [ToolErrorHandler]: {error_msg}")
                return ToolMessage(
                    content=error_msg,
                    name=request.tool_call.get("name", "unknown"),
                    tool_call_id=request.tool_call.get("id", ""),
                    status="error",
                )

    return ToolErrorHandlerMiddleware()


async def _load_mcp_tools_from_config(server_configs: dict) -> list:
    """Load MCP tools and register any that match a concurrency-limited group."""
    return await load_and_register_mcp_tools(
        server_configs, workspace_root=WORKSPACE_ROOT
    )


def _get_ifind_news_tools_sync(search_cfg) -> list:
    """Load ifind-news MCP tools synchronously (called during search tool setup)."""
    if not search_cfg.ifind_news_url:
        print("WARNING: ifind-news search configured but no URL set. Search disabled.")
        return []

    server_config = {
        "ifind-news": {
            "url": search_cfg.ifind_news_url.rstrip("/"),
            "transport": search_cfg.ifind_news_transport,
        }
    }
    headers = ifind_auth_headers()
    if headers:
        server_config["ifind-news"]["headers"] = headers

    async def _load():
        tools = await _load_mcp_tools_from_config(server_config)
        if tools:
            print(f"INFO: Loaded {len(tools)} ifind-news search tool(s)")
        else:
            print("WARNING: ifind-news returned 0 tools. Search disabled.")
        return tools

    try:
        return asyncio.run(_load())
    except RuntimeError:
        # Already in an event loop — use a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _load()).result()
    except Exception as e:
        print(f"WARNING: Failed to load ifind-news tools: {e}")
        return []


def _get_search_tools(cfg):
    """Return LangChain search tool(s) based on config.search.provider."""
    provider = cfg.search.provider
    if provider == "none" or not provider:
        return []

    if provider == "ifind-news":
        return _get_ifind_news_tools_sync(cfg.search)

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
                    description=(
                        "Search for financial data, market research, company filings, "
                        "industry reports, and current market events."
                    ),
                )
            ]
        except ImportError:
            print("WARNING: google-search-results not installed. Search disabled.")
            return []

    if provider == "duckduckgo":
        try:
            from langchain_community.tools import DuckDuckGoSearchResults
            return [DuckDuckGoSearchResults(max_results=cfg.search.max_results)]
        except ImportError:
            print("WARNING: duckduckgo-search not installed. Search disabled.")
            return []

    print(f"WARNING: Unknown search provider '{provider}'. Search disabled.")
    return []


async def _get_mcp_tools(cfg) -> list:
    """Load MCP tools from all configured servers that have a non-empty URL."""
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    server_names = mcp_server_names_for_tool_group(
        access_config,
        "mcp_tools",
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)
    if not server_configs:
        return []
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(f"INFO: Loaded {len(tools)} MCP tool(s) from: {list(server_configs.keys())}")
    return tools


async def _get_mcp_tool_groups(cfg, agent_name: str) -> dict[str, list]:
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    return {
        group_name: await _get_mcp_tools_for_group(cfg, group_name)
        for group_name in mcp_tool_group_names_for_agent(access_config, agent_name)
    }


async def _get_mcp_tools_for_group(cfg, group_name: str) -> list:
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    server_names = mcp_server_names_for_tool_group(
        access_config,
        group_name,
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)
    if not server_configs:
        return []
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(
            f"INFO: Loaded {len(tools)} MCP tool(s) for group '{group_name}' "
            f"from: {list(server_configs.keys())}"
        )
    return tools


def _local_tools() -> list:
    return [build_comps_excel, build_pptx]


async def _create_agent():
    """Build and return the deep agent."""
    if os.getenv("MARKET_RESEARCHER_TEST_MODE") == "1":
        return {
            "name": AGENT_NAME,
            "test_mode": True,
            "backend_type": "localshell",
        }

    try:
        from deepagents import create_deep_agent
    except ImportError as e:
        raise ImportError(
            "deepagents is not installed. Run: pip install deepagents"
        ) from e

    cfg = load_config()

    # System prompt from agents/market-researcher.md
    prompt_path = PROJECT_ROOT / "agents" / "market-researcher.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Agent prompt not found at {prompt_path}. "
            "Check that the project files are present."
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    model = build_chat_model_for_agent(WORKSPACE_ROOT, AGENT_NAME, timeout=120)

    # Gather tools
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    mcp_tool_groups = await _get_mcp_tool_groups(cfg, AGENT_NAME)
    search_tools = _get_search_tools(cfg)
    all_tools = resolve_agent_tools(
        AGENT_NAME,
        access_config=access_config,
        local_tools=build_tool_catalog(_local_tools()),
        dynamic_tool_groups={"search_tools": search_tools},
        mcp_tool_groups=mcp_tool_groups,
    )
    print(
        f"INFO: Agent tools — Total: {len(all_tools)}, "
        f"MCP groups: {_mcp_group_counts(mcp_tool_groups)}, "
        f"Search: {len(search_tools)}"
    )

    backend = build_backend(prefer_shell=True)
    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=all_tools,
        skills=[mirror_skills_into_backend(backend, PROJECT_ROOT / "skills")],
        middleware=[
            make_concurrency_limit_middleware(WORKSPACE_ROOT),
            _make_tool_error_middleware(),
        ],
        backend=backend,
        name=AGENT_NAME,
    )
    return agent


def _mcp_group_counts(mcp_tool_groups: dict[str, list]) -> dict[str, int]:
    return {
        group_name: len(tools)
        for group_name, tools in sorted(mcp_tool_groups.items())
    }


# Build synchronously so that langgraph.json can import `graph` at module level.
# langgraph dev loads this in a ThreadPoolExecutor (no event loop), so use asyncio.run().
try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise market_researcher agent: {exc}\n"
        "Check root tool-concurrency.yaml, model-routing.yaml, .env, and installed packages."
    ) from exc
