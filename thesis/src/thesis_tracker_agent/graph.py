"""Thesis Tracker - LangGraph Deep Agents graph."""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from thesis_tracker_agent.config import (  # noqa: E402
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)
from thesis_tracker_agent.tools import (  # noqa: E402
    create_task_output_dir,
    write_json_artifact,
    write_markdown_report,
)


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


async def _get_mcp_tools(cfg) -> list:
    if os.getenv("THESIS_TRACKER_DISABLE_MCP") == "1":
        return []

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
            timeout=120,
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


async def _create_agent():
    if os.getenv("THESIS_TRACKER_TEST_MODE") == "1":
        return {
            "name": "thesis_tracker",
            "test_mode": True,
            "backend_type": "filesystem",
        }

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()
    prompt_path = PROJECT_ROOT / "agents" / "thesis.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Agent prompt not found at {prompt_path}.")

    system_prompt = prompt_path.read_text(encoding="utf-8")
    model = _build_model(cfg)
    mcp_tools = await _get_mcp_tools(cfg)
    local_tools = [
        create_task_output_dir,
        write_markdown_report,
        write_json_artifact,
    ]
    all_tools = mcp_tools + local_tools

    print(f"INFO: Agent tools - MCP: {len(mcp_tools)}, Local: {len(local_tools)}")

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=all_tools,
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=[_make_tool_error_middleware()],
        backend=FilesystemBackend(root_dir=str(file_storage_root()), virtual_mode=False),
        name="thesis_tracker",
    )


try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise thesis_tracker agent: {exc}\n"
        "Check config.yaml, ../.env, and installed packages."
    ) from exc
