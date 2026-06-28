"""HTML Image Renderer - LangGraph Deep Agents graph."""

# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage, ToolMessage

from financial_agent_runtime import backend_is_daytona, upload_file_artifact


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SKILLS_DIR = PROJECT_ROOT / "skills"
_RENDER_HELPER_BACKEND_PATH: Path | None = None
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from html_image_renderer_agent.config import (  # noqa: E402
    WORKSPACE_ROOT,
    build_backend,
    mirror_skills_into_backend,
    file_storage_root,
    load_config,
    resolve_output_base,
)


def _render_helper_path() -> Path:
    """Return a shell-backend-visible render helper path."""
    script_path = PROJECT_ROOT / "src" / "html_image_renderer_agent" / "render_html.py"
    if not backend_is_daytona():
        return script_path

    global _RENDER_HELPER_BACKEND_PATH
    helper_path = file_storage_root() / ".helpers" / "html-image-renderer" / "render_html.py"
    if _RENDER_HELPER_BACKEND_PATH != helper_path:
        upload_file_artifact(script_path, helper_path)
        _RENDER_HELPER_BACKEND_PATH = helper_path
    return helper_path


def _make_runtime_context_middleware(context_factory):
    """Append fresh renderer runtime context to every model call."""
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
    """Catch tool errors and return them to the model for self-recovery."""
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


def _runtime_context_prompt(cfg) -> str:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    output_base = resolve_output_base(cfg.output.dir)
    render_script = _render_helper_path()
    return (
        "\n\n## Runtime Context\n"
        f"Current Beijing time: {now:%Y-%m-%d %H:%M:%S %Z}.\n"
        f"Current Beijing date: {now:%Y-%m-%d}.\n"
        f"Workspace root: {WORKSPACE_ROOT}.\n"
        f"Shared file storage root: {file_storage_root()}.\n"
        f"Default output base directory: {output_base}.\n"
        f"HTML Anything skills directory: {SKILLS_DIR}.\n"
        f"HTML render helper script: {render_script}.\n"
        "If the task provides output_dir (an upstream orchestrator dispatched you), "
        "treat it as your artifact root: write html/ and png/ directly under it and "
        "do not create a new top-level out/<timestamp>/ folder. If the task does not "
        "provide output_dir, create "
        f"{output_base}/{now:%Y%m%d-%H%M%S}/ as the task output directory. "
        "Inside output_dir, create html/ and png/ subdirectories, scan existing "
        "three-digit sequence numbers, and write the next paired files as "
        "html/<seq>.html and png/<seq>.png, for example html/001.html and "
        "png/001.png. Never overwrite an existing sequence. Always read "
        "source_paths yourself from the filesystem; do not "
        "ask the orchestrator to paste file contents. Use the mounted HTML "
        "Anything skills as design and layout guidance. Before writing HTML, "
        "select one primary skill, read its SKILL.md, and read the adjacent "
        "example.html in bounded structural slices when present so the output "
        "inherits the actual template structure rather than only the skill "
        "description. Adapt every selected "
        "skill to exactly one deliverable #image-root hero image in the selected HTML file, "
        "set data-html-anything-skill on #image-root to the selected skill id, "
        "render only that element to the paired png/<seq>.png, and keep the final response "
        "terse with paths, dimensions, selected skill, and status only.\n"
    )


def _is_allowed_model_gateway(parsed_base_url) -> bool:
    host = parsed_base_url.hostname or ""
    if parsed_base_url.scheme == "https" and parsed_base_url.netloc:
        return True
    return parsed_base_url.scheme == "http" and host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def _create_backend():
    return build_backend(prefer_shell=True)


def _create_agent():
    if os.getenv("HTML_IMAGE_RENDERER_TEST_MODE") == "1":
        return {
            "name": "html_image_renderer",
            "test_mode": True,
            "backend_type": "localshell",
            "backend_root": str(file_storage_root()),
            "skills": [str(SKILLS_DIR)],
        }

    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise ImportError("deepagents is not installed. Run: pip install deepagents") from exc

    cfg = load_config()

    prompt_path = PROJECT_ROOT / "agents" / "html-image-renderer.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Agent prompt not found at {prompt_path}. Check the project files."
        )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    model = _build_model(cfg)
    backend = _create_backend()

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[],
        skills=[mirror_skills_into_backend(backend, SKILLS_DIR)],
        middleware=[
            _make_runtime_context_middleware(lambda: _runtime_context_prompt(cfg)),
            _make_tool_error_middleware(),
        ],
        backend=backend,
        name="html_image_renderer",
    )


try:
    graph = _create_agent()
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise html_image_renderer agent: {exc}\n"
        "Check html-image-renderer/config.yaml, workspace .env, and installed packages."
    ) from exc
