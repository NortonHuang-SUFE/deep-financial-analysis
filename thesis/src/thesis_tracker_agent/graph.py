"""Thesis Tracker - LangGraph Deep Agents graph."""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from financial_agent_runtime import (  # noqa: E402
    build_chat_model_for_agent,
    build_tool_catalog,
    load_and_register_mcp_tools,
    load_tool_access_config,
    make_concurrency_limit_middleware,
    mcp_server_names_for_tool_group,
    mcp_tool_group_names_for_agent,
    resolve_agent_tools,
)

from thesis_tracker_agent.config import (  # noqa: E402
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    build_backend,
    mirror_skills_into_backend,
    load_config,
)
from thesis_tracker_agent.tools import (  # noqa: E402
    create_task_output_dir,
    write_json_artifact,
    write_markdown_report,
)


AGENT_NAME = "thesis_tracker"


def _make_tool_error_middleware():
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


async def _get_mcp_tools(cfg, *, group_name: str) -> list:
    if os.getenv("THESIS_TRACKER_DISABLE_MCP") == "1":
        return []

    access_config = load_tool_access_config(WORKSPACE_ROOT)
    server_names = mcp_server_names_for_tool_group(
        access_config,
        group_name,
        list(cfg.mcp),
    )
    server_configs = enabled_mcp_server_configs(cfg, server_names=server_names)
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(f"INFO: Loaded {len(tools)} MCP tool(s) from: {list(server_configs)}")
    return tools


async def _get_mcp_tool_groups(cfg, agent_name: str) -> dict[str, list]:
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    return {
        group_name: await _get_mcp_tools(cfg, group_name=group_name)
        for group_name in mcp_tool_group_names_for_agent(access_config, agent_name)
    }


def _local_tools() -> list:
    return [
        create_task_output_dir,
        write_markdown_report,
        write_json_artifact,
    ]


async def _create_agent():
    if os.getenv("THESIS_TRACKER_TEST_MODE") == "1":
        return {
            "name": AGENT_NAME,
            "test_mode": True,
            "backend_type": "filesystem",
        }

    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()
    prompt_path = PROJECT_ROOT / "agents" / "thesis.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Agent prompt not found at {prompt_path}.")

    system_prompt = prompt_path.read_text(encoding="utf-8")
    model = build_chat_model_for_agent(WORKSPACE_ROOT, AGENT_NAME, timeout=120)
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    mcp_tool_groups = await _get_mcp_tool_groups(cfg, AGENT_NAME)
    all_tools = resolve_agent_tools(
        AGENT_NAME,
        access_config=access_config,
        local_tools=build_tool_catalog(_local_tools()),
        mcp_tool_groups=mcp_tool_groups,
    )

    print(
        f"INFO: Agent tools - Total: {len(all_tools)}, "
        f"MCP groups: {_mcp_group_counts(mcp_tool_groups)}"
    )

    backend = build_backend(prefer_shell=False)
    return create_deep_agent(
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


def _mcp_group_counts(mcp_tool_groups: dict[str, list]) -> dict[str, int]:
    return {
        group_name: len(tools)
        for group_name, tools in sorted(mcp_tool_groups.items())
    }


try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise thesis_tracker agent: {exc}\n"
        "Check root tool-concurrency.yaml, model-routing.yaml, .env, and installed packages."
    ) from exc
