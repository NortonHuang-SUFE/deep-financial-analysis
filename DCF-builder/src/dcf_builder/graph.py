"""DCF Builder - LangGraph Deep Agents graph."""

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
# before importing dcf_builder.* modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dcf_builder.assumption_research import (
    ASSUMPTION_SUBAGENT_NAME,
    create_assumption_research_subagent_spec,
)
from financial_agent_runtime import (
    build_chat_model_for_agent,
    build_tool_catalog,
    describe_agent_tool_access,
    load_and_register_mcp_tools,
    load_tool_access_config,
    make_concurrency_limit_middleware,
    mcp_server_names_for_tool_group,
    mcp_tool_group_names_for_agent,
    resolve_agent_tools,
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


DCF_BUILDER_AGENT_NAME = "dcf_builder"


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


async def _get_mcp_tools(
    cfg,
    *,
    group_name: str,
) -> list:
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    server_names = mcp_server_names_for_tool_group(
        access_config,
        group_name,
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(
            f"INFO: Loaded {len(tools)} MCP tool(s) for group '{group_name}' "
            f"from: {list(server_configs)}"
        )
    return tools


async def _get_mcp_tool_groups(cfg, agent_names: list[str]) -> dict[str, list]:
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    group_names: list[str] = []
    for agent_name in agent_names:
        for group_name in mcp_tool_group_names_for_agent(access_config, agent_name):
            if group_name not in group_names:
                group_names.append(group_name)

    return {
        group_name: await _get_mcp_tools(cfg, group_name=group_name)
        for group_name in group_names
    }


def _local_tools() -> list:
    return [
        build_comps_excel,
        build_dcf_model,
        validate_dcf_model,
        write_assumption_analysis,
        write_valuation_summary,
    ]


async def _create_agent():
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    if os.getenv("DCF_BUILDER_TEST_MODE") == "1":
        return {
            "name": DCF_BUILDER_AGENT_NAME,
            "test_mode": True,
            "backend_type": "localshell",
            "agent_config": describe_agent_tool_access(
                access_config,
                DCF_BUILDER_AGENT_NAME,
            ),
            "assumption_agent_config": describe_agent_tool_access(
                access_config,
                ASSUMPTION_SUBAGENT_NAME,
            ),
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

    model = build_chat_model_for_agent(
        WORKSPACE_ROOT,
        DCF_BUILDER_AGENT_NAME,
        timeout=120,
    )
    mcp_tool_groups = await _get_mcp_tool_groups(
        cfg,
        [DCF_BUILDER_AGENT_NAME, ASSUMPTION_SUBAGENT_NAME],
    )
    search_tools = _get_search_tools(cfg)
    local_tools = build_tool_catalog(_local_tools())
    dynamic_tool_groups = {"search_tools": search_tools}
    all_tools = resolve_agent_tools(
        DCF_BUILDER_AGENT_NAME,
        access_config=access_config,
        local_tools=local_tools,
        dynamic_tool_groups=dynamic_tool_groups,
        mcp_tool_groups=mcp_tool_groups,
    )
    assumption_tools = resolve_agent_tools(
        ASSUMPTION_SUBAGENT_NAME,
        access_config=access_config,
        local_tools=local_tools,
        dynamic_tool_groups=dynamic_tool_groups,
        mcp_tool_groups=mcp_tool_groups,
    )
    backend = build_backend(prefer_shell=True)
    assumption_subagent = create_assumption_research_subagent_spec(
        model=build_chat_model_for_agent(
            WORKSPACE_ROOT,
            ASSUMPTION_SUBAGENT_NAME,
            timeout=120,
        ),
        tools=assumption_tools,
        middleware=[
            make_concurrency_limit_middleware(WORKSPACE_ROOT),
            _make_tool_error_middleware(),
        ],
        backend=backend,
    )

    print(
        f"INFO: Agent tools - Parent: {len(all_tools)}, "
        f"Assumption subagent: {len(assumption_tools)}, "
        f"MCP groups: {_mcp_group_counts(mcp_tool_groups)}, "
        f"Search: {len(search_tools)}"
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
        name=DCF_BUILDER_AGENT_NAME,
    )


def _mcp_group_counts(mcp_tool_groups: dict[str, list]) -> dict[str, int]:
    return {
        group_name: len(tools)
        for group_name, tools in sorted(mcp_tool_groups.items())
    }


try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise dcf_builder agent: {exc}\n"
        "Check root tool-concurrency.yaml, model-routing.yaml, .env, and installed packages."
    ) from exc
