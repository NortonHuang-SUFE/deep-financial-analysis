"""Factories for single-stock-coverage LangGraph debug entrypoints."""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
WORKSPACE_ROOT = PROJECT_ROOT.parent
DCF_SRC_ROOT = WORKSPACE_ROOT / "DCF-builder" / "src"
SKILL_VIEW_ROOT = PROJECT_ROOT / ".langgraph_api" / "skill-views"

for path in (SRC_ROOT, DCF_SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from single_stock_coverage_agent.agent_registry import (  # noqa: E402
    ROOT_AGENT_NAME,
    AgentSpec,
    SkillLibrary,
    get_agent_spec,
)
from single_stock_coverage_agent.config import (  # noqa: E402
    enabled_mcp_server_configs,
    load_config,
)
from single_stock_coverage_agent.tools import (  # noqa: E402
    build_integrated_three_statement_model,
    create_coverage_run_dir,
    update_run_manifest,
    validate_integrated_three_statement_model,
    write_coverage_state,
    write_json_artifact,
    write_markdown_artifact,
)


@dataclass
class AgentBuildContext:
    model: Any
    local_tools_by_name: dict[str, Any]
    mcp_tools_by_server: dict[str, list]
    backend: Any
    middleware: list
    dcf_tools_by_name: dict[str, Any] | None = None


def create_graph(agent_name: str = ROOT_AGENT_NAME):
    """Synchronously create one LangGraph graph/runnable by agent registry name."""
    try:
        return asyncio.run(create_graph_async(agent_name))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to initialise single-stock-coverage graph '{agent_name}': {exc}\n"
            "Check single-stock-coverage/config.yaml, workspace .env, and installed packages."
        ) from exc


async def create_graph_async(agent_name: str = ROOT_AGENT_NAME):
    """Create one registry-declared agent graph.

    Standalone task graphs preserve their nested children where they have any;
    leaf task graphs are created without siblings or parents.
    """
    spec = get_agent_spec(agent_name)
    if os.getenv("SINGLE_STOCK_COVERAGE_TEST_MODE") == "1":
        return _test_graph(spec)

    try:
        from deepagents.backends import FilesystemBackend
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()
    model = _build_model(cfg)
    required_mcp_servers = _required_mcp_servers(spec)
    mcp_tools_by_server = (
        {}
        if os.getenv("SINGLE_STOCK_COVERAGE_DISABLE_MCP") == "1"
        else await _get_mcp_tools_by_server(cfg, required_mcp_servers)
    )
    local_tools_by_name = _tools_by_name(_local_tools())
    backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=False)
    middleware = [_make_tool_error_middleware()]
    context = AgentBuildContext(
        model=model,
        local_tools_by_name=local_tools_by_name,
        mcp_tools_by_server=mcp_tools_by_server,
        backend=backend,
        middleware=middleware,
    )

    print(
        f"INFO: Single Stock Coverage graph '{spec.graph_name}' ({spec.name}); "
        f"children: {len(spec.child_agents)}, MCP servers: {len(mcp_tools_by_server)}, "
        f"Local tools: {len(local_tools_by_name)}."
    )
    return _build_agent_runnable(spec, context)


def _test_graph(spec: AgentSpec) -> dict:
    return {
        "name": spec.name,
        "graph_name": spec.graph_name,
        "test_mode": True,
        "local_tools": list(spec.local_tools),
        "mcp_servers": list(spec.mcp_servers),
        "dcf_tools": list(spec.dcf_tools),
        "skills": [f"{library}:{skill}" for library, skill in spec.skills],
        "child_agents": list(spec.child_agents),
    }


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
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("WARNING: langchain-mcp-adapters not installed. MCP tools disabled.")
        return []

    if not server_configs:
        return []

    try:
        client = MultiServerMCPClient(server_configs)
        return await client.get_tools()
    except Exception as exc:
        print(f"WARNING: Could not connect to MCP server(s): {exc}")
        return []


async def _get_mcp_tools_by_server(cfg, server_names: set[str]) -> dict[str, list]:
    enabled_servers = enabled_mcp_server_configs(cfg)
    tools_by_server: dict[str, list] = {}
    for server_name in sorted(server_names):
        server_config = enabled_servers.get(server_name)
        if not server_config:
            continue
        tools_by_server[server_name] = await _load_mcp_tools_from_config(
            {server_name: server_config}
        )

    loaded_count = sum(len(tools) for tools in tools_by_server.values())
    if loaded_count:
        print(
            f"INFO: Loaded {loaded_count} MCP tool(s) from: "
            f"{list(tools_by_server)}"
        )
    return tools_by_server


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
                "DASHSCOPE_API_KEY, or ALIBABA_API_KEY in the workspace .env."
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
            timeout=300,
        )
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


def _local_tools() -> list:
    return [
        create_coverage_run_dir,
        write_markdown_artifact,
        write_json_artifact,
        update_run_manifest,
        write_coverage_state,
        build_integrated_three_statement_model,
        validate_integrated_three_statement_model,
    ]


def _dcf_tools() -> list:
    try:
        from dcf_builder.tools import (
            build_comps_excel,
            build_dcf_model,
            validate_dcf_model,
            write_assumption_analysis,
            write_valuation_summary,
        )
    except Exception as exc:
        print(f"WARNING: DCF execution tools disabled: {exc}")
        return []

    return [
        build_comps_excel,
        build_dcf_model,
        validate_dcf_model,
        write_assumption_analysis,
        write_valuation_summary,
    ]


def _tools_by_name(tools: list) -> dict[str, Any]:
    return {tool.name: tool for tool in tools}


def _read_prompt(filename: str) -> str:
    path = PROJECT_ROOT / "agents" / filename
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt not found at {path}")
    return path.read_text(encoding="utf-8")


def _build_agent_runnable(spec: AgentSpec, context: AgentBuildContext):
    from deepagents import create_deep_agent

    nested_subagents = [
        _build_subagent_spec(get_agent_spec(child_name), context)
        for child_name in spec.child_agents
    ]
    return create_deep_agent(
        model=context.model,
        system_prompt=_system_prompt(spec),
        tools=_tools_for_spec(spec, context),
        subagents=nested_subagents,
        skills=_skill_sources_for_spec(spec),
        middleware=context.middleware,
        backend=context.backend,
        name=spec.name,
    )


def _build_subagent_spec(spec: AgentSpec, context: AgentBuildContext) -> dict:
    return {
        "name": spec.name,
        "description": spec.description,
        "runnable": _build_agent_runnable(spec, context),
    }


def _system_prompt(spec: AgentSpec) -> str:
    if spec.prompt_file:
        return _read_prompt(spec.prompt_file)
    if spec.inline_prompt:
        return spec.inline_prompt
    raise ValueError(f"Agent '{spec.name}' has no prompt source configured.")


def _tools_for_spec(spec: AgentSpec, context: AgentBuildContext) -> list:
    tools = []
    for tool_name in spec.local_tools:
        tools.append(_lookup_tool(context.local_tools_by_name, tool_name, spec.name))
    for server_name in spec.mcp_servers:
        tools.extend(context.mcp_tools_by_server.get(server_name, []))
    if spec.dcf_tools and context.dcf_tools_by_name is None:
        context.dcf_tools_by_name = _tools_by_name(_dcf_tools())
    for tool_name in spec.dcf_tools:
        tools.append(_lookup_tool(context.dcf_tools_by_name or {}, tool_name, spec.name))
    return tools


def _lookup_tool(tools_by_name: dict[str, Any], tool_name: str, agent_name: str) -> Any:
    try:
        return tools_by_name[tool_name]
    except KeyError as exc:
        known = ", ".join(sorted(tools_by_name))
        raise KeyError(
            f"Tool '{tool_name}' configured for agent '{agent_name}' is not available. "
            f"Known tools: {known}"
        ) from exc


def _required_mcp_servers(spec: AgentSpec) -> set[str]:
    required = set(spec.mcp_servers)
    for child_name in spec.child_agents:
        required.update(_required_mcp_servers(get_agent_spec(child_name)))
    return required


def _skill_sources_for_spec(spec: AgentSpec) -> list[str] | None:
    if not spec.skills:
        return None

    view_root = SKILL_VIEW_ROOT / spec.name
    _reset_generated_skill_view(view_root)
    for library, skill_name in spec.skills:
        source_dir = _skill_dir(library, skill_name)
        target = view_root / skill_name
        try:
            target.symlink_to(source_dir, target_is_directory=True)
        except OSError:
            shutil.copytree(source_dir, target)
    return [str(view_root)]


def _reset_generated_skill_view(view_root: Path) -> None:
    if not _is_generated_skill_view_path(view_root):
        raise ValueError(f"Refusing to reset non-generated skill view path: {view_root}")
    if view_root.is_symlink():
        view_root.unlink()
    elif view_root.exists():
        shutil.rmtree(view_root)
    view_root.mkdir(parents=True, exist_ok=True)


def _is_generated_skill_view_path(path: Path) -> bool:
    try:
        path.resolve().relative_to(SKILL_VIEW_ROOT.resolve())
    except ValueError:
        return False
    return path != SKILL_VIEW_ROOT


def _skill_dir(library: SkillLibrary, skill_name: str) -> Path:
    if library == "single_stock_coverage":
        path = PROJECT_ROOT / "skills" / skill_name
    elif library == "dcf_builder":
        path = WORKSPACE_ROOT / "DCF-builder" / "skills" / skill_name
    else:
        raise ValueError(f"Unknown skill library '{library}'.")

    if not (path / "SKILL.md").exists():
        raise FileNotFoundError(f"Configured skill '{library}:{skill_name}' not found at {path}")
    return path
