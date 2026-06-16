"""Market Researcher — LangGraph Deep Agents graph.

This module builds the agent using deepagents.create_deep_agent() and
exposes a `graph` object that langgraph.json points to.

Skills in ./skills/ are auto-discovered by deepagents.
MCP tools are loaded from config.yaml at startup.
Search tools are selected by the configured provider.
Local tools (build_comps_excel, build_pptx) are always available.
"""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain.chat_models import init_chat_model
from langchain_core.messages import ToolMessage

# LangGraph loads this file by path, so make the src-layout package importable
# before importing market_researcher.* modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from market_researcher.config import (
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    ifind_auth_headers,
    load_config,
)
from market_researcher.tools import build_comps_excel, build_pptx


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
    """Load tools from MCP servers using the new (non-context-manager) API."""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("WARNING: langchain-mcp-adapters not installed. MCP tools disabled.")
        return []

    try:
        client = MultiServerMCPClient(server_configs)
        tools = await client.get_tools()
        return tools
    except Exception as e:
        print(f"WARNING: Could not connect to MCP server(s): {e}")
        return []


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
    server_configs = enabled_mcp_server_configs(cfg)
    if not server_configs:
        return []
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(f"INFO: Loaded {len(tools)} MCP tool(s) from: {list(server_configs.keys())}")
    return tools


async def _create_agent():
    """Build and return the deep agent."""
    if os.getenv("MARKET_RESEARCHER_TEST_MODE") == "1":
        return {
            "name": "market_researcher",
            "test_mode": True,
            "backend_type": "localshell",
        }

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend
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

    # Initialise model
    model_id = cfg.model.default

    if cfg.model.base_url:
        # Custom OpenAI-compatible endpoint — use ChatOpenAI directly
        from langchain_openai import ChatOpenAI
        import httpx

        base_url = cfg.model.base_url.rstrip("/")
        allowed_hosts = (
            "api.babelark.com",
            "api.minimaxi.com",
            "api.minimax.io",
            "api.deepseek.com",
            "dashscope.aliyuncs.com",
        )
        parsed_base_url = urlparse(base_url)
        if parsed_base_url.scheme != "https" or parsed_base_url.netloc.lower() not in allowed_hosts:
            raise ValueError(
                "model.base_url must use BabelArk, MiniMax, DeepSeek, or Alibaba DashScope API: "
                f"{', '.join(f'https://{host}' for host in allowed_hosts)}"
            )
        if not cfg.model.api_key:
            if "babelark.com" in base_url:
                env_name = "BABELARK_API_KEY"
            elif "minimax" in base_url:
                env_name = "MINIMAX_API_KEY"
            elif "dashscope.aliyuncs.com" in base_url:
                env_name = "DASHSCOPE_API_KEY"
            else:
                env_name = "DEEPSEEK_API_KEY"
            raise ValueError(
                f"Missing model API key. Set {env_name} in .env, "
                "or set model.api_key in config.yaml."
            )
        if not base_url.endswith("/v1"):
            base_url += "/v1"

        # Detect proxy from env for async httpx client
        proxy_url = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")

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
        if proxy_url:
            model_kwargs["http_async_client"] = httpx.AsyncClient(proxy=proxy_url, verify=False)
            model_kwargs["http_client"] = httpx.Client(proxy=proxy_url, verify=False)

        model = ChatOpenAI(**model_kwargs)
    else:
        # Standard provider — use init_chat_model with provider prefix
        model_kwargs: dict = {"max_tokens": cfg.model.max_tokens}
        if cfg.model.api_key:
            model_kwargs["api_key"] = cfg.model.api_key
        if ":" not in model_id:
            model_id = f"openai:{model_id}"
        model = init_chat_model(model_id, **model_kwargs)

    # Gather tools
    mcp_tools = await _get_mcp_tools(cfg)
    search_tools = _get_search_tools(cfg)
    local_tools = [build_comps_excel, build_pptx]

    all_tools = mcp_tools + search_tools + local_tools
    print(
        f"INFO: Agent tools — MCP: {len(mcp_tools)}, "
        f"Search: {len(search_tools)}, Local: {len(local_tools)}"
    )

    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=all_tools,
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=[_make_tool_error_middleware()],
        backend=LocalShellBackend(
            root_dir=str(file_storage_root()),
            virtual_mode=False,
            inherit_env=True,
        ),
        name="market_researcher",
    )
    return agent


# Build synchronously so that langgraph.json can import `graph` at module level.
# langgraph dev loads this in a ThreadPoolExecutor (no event loop), so use asyncio.run().
try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise market_researcher agent: {exc}\n"
        "Check config.yaml and ensure required packages are installed."
    ) from exc
