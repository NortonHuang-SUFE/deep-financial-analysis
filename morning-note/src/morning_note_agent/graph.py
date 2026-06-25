"""Morning Note - LangGraph Deep Agents graph."""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import contextmanager
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

from morning_note_agent.config import (  # noqa: E402
    enabled_mcp_server_configs,
    file_storage_root,
    load_config,
)
from morning_note_agent.tools import (  # noqa: E402
    create_task_output_dir,
    write_json_artifact,
    write_markdown_report,
)


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


# ── Deep Agents harness profile ───────────────────────────────────────────────


@contextmanager
def _general_purpose_subagent_disabled(model):
    """Temporarily disable Deep Agents' auto-added general-purpose subagent."""
    from deepagents import (
        GeneralPurposeSubagentProfile,
        HarnessProfile,
        register_harness_profile,
    )
    from deepagents._models import get_model_provider
    from deepagents.profiles.harness import harness_profiles

    harness_profiles._ensure_harness_profiles_loaded()
    original_profiles = dict(harness_profiles._HARNESS_PROFILES)
    provider = get_model_provider(model) or "openai"

    try:
        register_harness_profile(
            provider,
            HarnessProfile(
                general_purpose_subagent=GeneralPurposeSubagentProfile(
                    enabled=False
                ),
            ),
        )
        yield
    finally:
        harness_profiles._HARNESS_PROFILES.clear()
        harness_profiles._HARNESS_PROFILES.update(original_profiles)


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


def _runtime_context_prompt(cfg) -> str:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    return (
        "\n\n## Runtime Context\n"
        f"Current Beijing time: {now:%Y-%m-%d %H:%M:%S %Z}.\n"
        f"Current Beijing date: {now:%Y-%m-%d}.\n"
        f"Default output base directory: {cfg.output.dir}.\n"
        f"Shared file storage root: {file_storage_root()}.\n"
        "Resolve relative market dates from this Beijing date/time. Write all "
        "artifacts through the provided artifact tools and report the absolute "
        "paths returned by those tools. Do not reuse artifact paths from previous "
        "runs unless the user explicitly asks to inspect an old run.\n"
    )


def _is_allowed_model_gateway(parsed_base_url) -> bool:
    host = parsed_base_url.hostname or ""
    if parsed_base_url.scheme == "https" and parsed_base_url.netloc:
        return True
    return parsed_base_url.scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}


async def _create_agent():
    if os.getenv("MORNING_NOTE_TEST_MODE") == "1":
        return {
            "name": "morning_note",
            "test_mode": True,
            "backend_type": "filesystem",
        }

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()

    prompt_path = PROJECT_ROOT / "agents" / "morning-note.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Agent prompt not found at {prompt_path}. Check the project files."
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    model = _build_model(cfg)
    mcp_tools = await _get_mcp_tools(cfg)
    local_tools = [
        create_task_output_dir,
        write_markdown_report,
        write_json_artifact,
    ]
    backend = FilesystemBackend(root_dir=str(file_storage_root()), virtual_mode=False)
    all_tools = mcp_tools + local_tools

    print(
        f"INFO: Agent tools - MCP: {len(mcp_tools)}, Local: {len(local_tools)}"
    )

    with _general_purpose_subagent_disabled(model):
        return create_deep_agent(
            model=model,
            system_prompt=system_prompt,
            tools=all_tools,
            skills=[str(PROJECT_ROOT / "skills")],
            middleware=[
                _make_runtime_context_middleware(lambda: _runtime_context_prompt(cfg)),
                _make_tool_error_middleware(),
            ],
            backend=backend,
            name="morning_note",
        )


try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise morning_note agent: {exc}\n"
        "Check config.yaml, ../.env, and installed packages."
    ) from exc
