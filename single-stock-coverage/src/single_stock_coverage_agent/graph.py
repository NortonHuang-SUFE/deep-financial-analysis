"""Single Stock Coverage - LangGraph Deep Agents graph."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from langchain_core.messages import ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
WORKSPACE_ROOT = PROJECT_ROOT.parent
DCF_SRC_ROOT = WORKSPACE_ROOT / "DCF-builder" / "src"

for path in (SRC_ROOT, DCF_SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from single_stock_coverage_agent.config import (  # noqa: E402
    enabled_mcp_server_configs,
    load_config,
)
from single_stock_coverage_agent.tools import (  # noqa: E402
    create_coverage_run_dir,
    update_run_manifest,
    write_coverage_state,
    write_json_artifact,
    write_markdown_artifact,
)


_TASK_SUBAGENTS: dict[str, tuple[str, str]] = {
    "task1_company_researcher": (
        "task1-company-researcher.md",
        "Task 1 Company Research: produces company_research.md, "
        "business_driver_map.json, and source_log.json for one target company.",
    ),
    "task2_financial_modeler": (
        "task2-financial-modeler.md",
        "Task 2 Financial Modeling: parent coordinator that delegates Income "
        "Statement, Balance Sheet, and Cash Flow Statement tabs to three child "
        "subagents (is_modeler, bs_modeler, cf_modeler), then runs inter-statement "
        "consistency checks, populates DCF Inputs, runs audit-xls, and writes "
        "model_audit.md.",
    ),
    "task3_valuation_analyst": (
        "task3-valuation-analyst.md",
        "Task 3 Valuation Analysis: parent that runs evidence gate, value-driver "
        "map, assumption audit, and valuation reconciliation. Delegates assumption "
        "generation to assumption_generator child and DCF/comps execution to "
        "dcf_execution child.",
    ),
    "task4_chart_pack_generator": (
        "task4-chart-pack-generator.md",
        "Task 4 Chart Generation: creates a chart pack and chart_index.json "
        "from Task 1-3 artifacts without new research.",
    ),
    "task5_report_assembler": (
        "task5-report-assembler.md",
        "Task 5 Report Assembly: creates initiation reports or update memos "
        "from Task 1-4 artifacts without changing upstream conclusions.",
    ),
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


def _read_prompt(filename: str) -> str:
    path = PROJECT_ROOT / "agents" / filename
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt not found at {path}")
    return path.read_text(encoding="utf-8")


# ── Task 2 child subagent specs ─────────────────────────────────────────────


def _create_is_modeler_subagent_spec(*, model, tools: list, backend, middleware: list) -> dict:
    from deepagents import create_deep_agent

    runnable = create_deep_agent(
        model=model,
        system_prompt=_read_prompt("task2-is-modeler.md"),
        tools=tools,
        subagents=[],
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=middleware,
        backend=backend,
        name="is_modeler",
    )
    return {
        "name": "is_modeler",
        "description": (
            "Income Statement and Revenue Build modeler. Owned by Task 2 parent. "
            "Builds the Revenue Build tab and Income Statement tab in integrated_model.xlsx."
        ),
        "runnable": runnable,
    }


def _create_bs_modeler_subagent_spec(*, model, tools: list, backend, middleware: list) -> dict:
    from deepagents import create_deep_agent

    runnable = create_deep_agent(
        model=model,
        system_prompt=_read_prompt("task2-bs-modeler.md"),
        tools=tools,
        subagents=[],
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=middleware,
        backend=backend,
        name="bs_modeler",
    )
    return {
        "name": "bs_modeler",
        "description": (
            "Balance Sheet modeler. Owned by Task 2 parent. "
            "Builds the Balance Sheet tab in integrated_model.xlsx after is_modeler completes."
        ),
        "runnable": runnable,
    }


def _create_cf_modeler_subagent_spec(*, model, tools: list, backend, middleware: list) -> dict:
    from deepagents import create_deep_agent

    runnable = create_deep_agent(
        model=model,
        system_prompt=_read_prompt("task2-cf-modeler.md"),
        tools=tools,
        subagents=[],
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=middleware,
        backend=backend,
        name="cf_modeler",
    )
    return {
        "name": "cf_modeler",
        "description": (
            "Cash Flow Statement modeler. Owned by Task 2 parent. "
            "Builds the Cash Flow Statement tab in integrated_model.xlsx after is_modeler "
            "and bs_modeler complete, and wires the BS Cash cross-link."
        ),
        "runnable": runnable,
    }


# ── Task 3 child subagent specs ─────────────────────────────────────────────


def _create_assumption_generator_subagent_spec(
    *, model, tools: list, mcp_tools: list, backend, middleware: list
) -> dict:
    from deepagents import create_deep_agent

    runnable = create_deep_agent(
        model=model,
        system_prompt=_read_prompt("task3-assumption-generator.md"),
        tools=list(mcp_tools) + list(tools),
        subagents=[],
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=middleware,
        backend=backend,
        name="assumption_generator",
    )
    return {
        "name": "assumption_generator",
        "description": (
            "DCF assumption generation subagent for Task 3. Receives the value driver map, "
            "Task 1 and Task 2 artifacts, and any assumption audit feedback. Returns a "
            "Bear/Base/Bull assumption pack (assumption_pack.md content) to the Task 3 parent."
        ),
        "runnable": runnable,
    }


def _create_dcf_execution_subagent_spec(*, model, tools: list, backend, middleware: list) -> dict:
    from deepagents import create_deep_agent

    prompt = """# DCF Execution Subagent

You are the nested DCF execution subagent for Task 3 valuation. You only run
after the valuation analyst has produced and audited an assumption pack.

Your job is to convert audited DCF inputs into deterministic artifacts:

- comparable-company workbook when requested
- DCF model workbook with Bear/Base/Bull cases and three 5x5 sensitivity tables
- validation JSON / validation findings
- valuation summary

Use the local DCF tools when available. Treat the parent valuation analyst's
assumption pack as the source of scenario inputs. Do not invent missing
assumptions; return a clear blocker if required fields are absent.

Return a structured summary to the parent including:
- paths to dcf_model.xlsx, comps.xlsx, and any validation artifacts
- DCF equity value per share (Bear/Base/Bull)
- implied EV/EBITDA at Base case
- any validation warnings
"""

    runnable = create_deep_agent(
        model=model,
        system_prompt=prompt,
        tools=tools,
        subagents=[],
        skills=[str(WORKSPACE_ROOT / "DCF-builder" / "skills")],
        middleware=middleware,
        backend=backend,
        name="dcf_execution",
    )
    return {
        "name": "dcf_execution",
        "description": (
            "Nested DCF executor for audited valuation assumptions. Builds "
            "comps and DCF workbooks with validation using current DCF-builder "
            "tool capability."
        ),
        "runnable": runnable,
    }


def _create_task_subagent_spec(
    *,
    name: str,
    prompt_filename: str,
    description: str,
    model,
    tools: list,
    mcp_tools: list,
    backend,
    middleware: list,
) -> dict:
    from deepagents import create_deep_agent

    nested_subagents = []
    task_tools = list(mcp_tools) + list(tools)

    if name == "task2_financial_modeler":
        nested_subagents = [
            _create_is_modeler_subagent_spec(
                model=model,
                tools=tools,
                backend=backend,
                middleware=middleware,
            ),
            _create_bs_modeler_subagent_spec(
                model=model,
                tools=tools,
                backend=backend,
                middleware=middleware,
            ),
            _create_cf_modeler_subagent_spec(
                model=model,
                tools=tools,
                backend=backend,
                middleware=middleware,
            ),
        ]

    elif name == "task3_valuation_analyst":
        dcf_tools = _dcf_tools()
        nested_subagents = [
            _create_assumption_generator_subagent_spec(
                model=model,
                tools=tools,
                mcp_tools=mcp_tools,
                backend=backend,
                middleware=middleware,
            ),
            _create_dcf_execution_subagent_spec(
                model=model,
                tools=dcf_tools + list(tools),
                backend=backend,
                middleware=middleware,
            ),
        ]

    runnable = create_deep_agent(
        model=model,
        system_prompt=_read_prompt(prompt_filename),
        tools=task_tools,
        subagents=nested_subagents,
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=middleware,
        backend=backend,
        name=name,
    )
    return {"name": name, "description": description, "runnable": runnable}


def _create_task_subagents(*, model, tools: list, mcp_tools: list, backend, middleware: list) -> list[dict]:
    return [
        _create_task_subagent_spec(
            name=name,
            prompt_filename=prompt_filename,
            description=description,
            model=model,
            tools=tools,
            mcp_tools=mcp_tools,
            backend=backend,
            middleware=middleware,
        )
        for name, (prompt_filename, description) in _TASK_SUBAGENTS.items()
    ]


async def _create_agent():
    if os.getenv("SINGLE_STOCK_COVERAGE_TEST_MODE") == "1":
        return {"name": "single_stock_coverage", "test_mode": True}

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()
    model = _build_model(cfg)
    mcp_tools = [] if os.getenv("SINGLE_STOCK_COVERAGE_DISABLE_MCP") == "1" else await _get_mcp_tools(cfg)
    local_tools = _local_tools()
    backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=False)
    middleware = [_make_tool_error_middleware()]
    subagents = _create_task_subagents(
        model=model,
        tools=local_tools,
        mcp_tools=mcp_tools,
        backend=backend,
        middleware=middleware,
    )

    prompt_path = PROJECT_ROOT / "agents" / "single-stock-coverage.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Agent prompt not found at {prompt_path}.")

    print(
        f"INFO: Single Stock Coverage - {len(subagents)} task subagents; "
        f"MCP: {len(mcp_tools)}, Local: {len(local_tools)}."
    )
    return create_deep_agent(
        model=model,
        system_prompt=prompt_path.read_text(encoding="utf-8"),
        tools=local_tools,
        subagents=subagents,
        skills=[str(PROJECT_ROOT / "skills")],
        middleware=middleware,
        backend=backend,
        name="single_stock_coverage",
    )


try:
    graph = asyncio.run(_create_agent())
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise single_stock_coverage agent: {exc}\n"
        "Check single-stock-coverage/config.yaml, workspace .env, and installed packages."
    ) from exc
