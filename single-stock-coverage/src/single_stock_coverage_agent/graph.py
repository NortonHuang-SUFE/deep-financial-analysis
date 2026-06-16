"""LangGraph factory entrypoints for Single Stock Coverage Deep Agents."""

# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
WORKSPACE_ROOT = PROJECT_ROOT.parent
DCF_SRC_ROOT = WORKSPACE_ROOT / "DCF-builder" / "src"

for path in (SRC_ROOT, DCF_SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from single_stock_coverage_agent.agent_registry import (  # noqa: E402
    ToolGroupResolver,
    agent_uses_tool_group,
    create_registered_agent,
    describe_agent,
    load_agent_registry,
)
from single_stock_coverage_agent.config import (  # noqa: E402
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)


LOCAL_SHELL_AGENT_NAMES = {
    "single_stock_coverage",
    "workbook_builder",
    "model_update_executor",
    "dcf_execution",
    "task4_chart_pack_generator",
}


def _make_tool_error_middleware():
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


async def _get_mcp_tools(cfg) -> list:
    server_configs = enabled_mcp_server_configs(cfg)
    tools = await _load_mcp_tools_from_config(server_configs)
    if tools:
        print(f"INFO: Loaded {len(tools)} MCP tool(s) from: {list(server_configs)}")
    return tools


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
            model_kwargs["http_async_client"] = httpx.AsyncClient(
                proxy=proxy_url,
                verify=False,
            )
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


async def _create_agent(agent_name: str):
    registry = load_agent_registry()
    if os.getenv("SINGLE_STOCK_COVERAGE_TEST_MODE") == "1":
        return {
            "name": agent_name,
            "test_mode": True,
            "agent_config": describe_agent(registry, agent_name),
            "backend_type": _backend_type_for_agent(agent_name),
            "backend_map": _agent_backend_type_map(registry, agent_name),
        }

    try:
        from deepagents.backends import FilesystemBackend, LocalShellBackend
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()
    model = _build_model(cfg)
    needs_mcp = agent_uses_tool_group(registry, agent_name, "mcp_tools")
    mcp_tools = []
    if needs_mcp and os.getenv("SINGLE_STOCK_COVERAGE_DISABLE_MCP") != "1":
        mcp_tools = await _get_mcp_tools(cfg)

    backend_cache: dict[str, object] = {}

    def backend_resolver(name: str):
        if name not in backend_cache:
            root_dir = str(file_storage_root())
            if _uses_local_shell_backend(name):
                backend_cache[name] = LocalShellBackend(
                    root_dir=root_dir,
                    virtual_mode=False,
                    inherit_env=True,
                )
            else:
                backend_cache[name] = FilesystemBackend(
                    root_dir=root_dir,
                    virtual_mode=False,
                )
        return backend_cache[name]

    tool_resolver = ToolGroupResolver(mcp_tools=mcp_tools)
    middleware = [_make_tool_error_middleware()]
    runnable = create_registered_agent(
        agent_name,
        registry=registry,
        model=model,
        tool_resolver=tool_resolver,
        backend_resolver=backend_resolver,
        middleware=middleware,
    )
    agent_config = describe_agent(registry, agent_name)
    print(
        f"INFO: Single Stock Coverage agent '{agent_name}' ready; "
        f"tool groups: {agent_config['tool_groups']}; "
        f"subagents: {agent_config['subagents']}; "
        f"backend: {_backend_type_for_agent(agent_name)}; MCP: {len(mcp_tools)}."
    )
    return runnable


def _uses_local_shell_backend(agent_name: str) -> bool:
    return agent_name in LOCAL_SHELL_AGENT_NAMES


def _backend_type_for_agent(agent_name: str) -> str:
    return "localshell" if _uses_local_shell_backend(agent_name) else "filesystem"


def _agent_backend_type_map(registry, agent_name: str) -> dict[str, str]:
    spec = registry.agent(agent_name)
    backend_map = {agent_name: _backend_type_for_agent(agent_name)}
    for child_name in spec.subagents:
        backend_map.update(_agent_backend_type_map(registry, child_name))
    return backend_map


async def graph():
    return await _create_agent("single_stock_coverage")


async def task1_company_researcher_graph():
    return await _create_agent("task1_company_researcher")


async def task2_financial_modeler_graph():
    return await _create_agent("task2_financial_modeler")


async def task2_financial_facts_modeler_graph():
    return await _create_agent("financial_facts_modeler")


async def task2_is_modeler_graph():
    return await _create_agent("is_modeler")


async def task2_bs_modeler_graph():
    return await _create_agent("bs_modeler")


async def task2_cf_modeler_graph():
    return await _create_agent("cf_modeler")


async def task2_model_update_executor_graph():
    return await _create_agent("model_update_executor")


async def task2_workbook_builder_graph():
    return await _create_agent("workbook_builder")


async def task3_valuation_analyst_graph():
    return await _create_agent("task3_valuation_analyst")


async def task3_assumption_generator_graph():
    return await _create_agent("assumption_generator")


async def task3_dcf_execution_graph():
    return await _create_agent("dcf_execution")


async def task4_chart_pack_generator_graph():
    return await _create_agent("task4_chart_pack_generator")


async def task5_report_assembler_graph():
    return await _create_agent("task5_report_assembler")
