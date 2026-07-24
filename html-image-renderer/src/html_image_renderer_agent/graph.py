"""HTML Image Renderer - LangGraph Deep Agents graph."""

# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import ToolMessage

from financial_agent_runtime import (
    backend_is_daytona,
    build_chat_model_for_agent,
    make_runtime_context_middleware,
    upload_file_artifact,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SKILLS_DIR = PROJECT_ROOT / "skills"
AGENT_NAME = "html_image_renderer"
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
        "treat it as your artifact root: write html/, png/, and any skill-declared "
        "companion directory directly under it and do not create a new top-level "
        "out/<timestamp>/ folder. If the task does not "
        "provide output_dir, create "
        f"{output_base}/{now:%Y%m%d-%H%M%S}/ as the task output directory. "
        "Inside output_dir, create html/ and png/ subdirectories, scan existing "
        "three-digit sequence numbers, and write the next paired files as "
        "html/<seq>.html and png/<seq>.png, for example html/001.html and "
        "png/001.png. When the selected skill declares a same-sequence companion "
        "artifact, also create its requested sibling directory and file, follow "
        "that skill's validator and QA instructions, and report its absolute "
        "path. Never overwrite an existing sequence. Always read "
        "source_paths yourself from the filesystem; do not "
        "ask the orchestrator to paste file contents. Use the mounted HTML "
        "Anything skills as design and layout guidance. Before writing HTML, "
        "select one primary skill, read its SKILL.md, derive the skill directory "
        "from that SKILL.md path, follow its Assets section, and read "
        "assets/example.html in bounded structural slices when present "
        "(falling back to the legacy adjacent example.html only when needed) "
        "so the output inherits the actual template structure rather than only "
        "the skill description. Adapt every selected "
        "skill to exactly one deliverable #image-root hero image in the selected HTML file, "
        "set data-html-anything-skill on #image-root to the selected skill id, "
        "render only that element to the paired png/<seq>.png, then visually inspect "
        "the actual PNG before finishing. Check for blank output, clipped or overflowing "
        "text, overlapping elements, unreadable type, broken charts/tables, wrong aspect "
        "ratio, footer collisions, and inconsistent market color semantics. If an obvious "
        "formatting issue is visible, revise the HTML and render the next unused sequence "
        "until the accepted PNG passes visual QA. Keep the final response terse with paths, "
        "dimensions, selected skill, visual-QA status, and any skill-declared "
        "companion-validation status only.\n"
        "\n## Render Helper Interface\n"
        f"Run `{render_script}` with --html and --png (absolute paths), "
        "--selector (default #image-root), --width and --height (viewport, "
        "default 1080x1440; the screenshot is of the element, so a tall "
        "#image-root is captured in full), and --device-scale-factor (default "
        "1). It prints one JSON line with html_path, png_path, width, height "
        "and html_anything_skill, or `ERROR: ...` on stderr with exit code 1. "
        "That is the complete interface; do not read the helper's source to "
        "discover flags.\n"
        "\n## QA Image Protocol\n"
        "Reading an image returns an image content block, and image blocks are "
        "exempt from the large-tool-result eviction that trims text, so every "
        "image you read stays in the conversation and is resent on every later "
        "model call. Produce one downscaled QA image per accepted sequence in a "
        "single execute call (longest side at most 1600px, JPEG quality 75) and "
        "read_file that one file exactly once. Do not read_file the "
        "full-resolution deliverable PNG, do not read the same image twice, do "
        "not slice a tall image into sections and read each one, and do not "
        "probe pixels with PIL loops. Verify text, numbers, dates and color "
        "semantics with grep against html/<seq>.html instead of re-reading "
        "images.\n"
        "\n## Deliverable Checklist\n"
        "Your todo list must carry one item per artifact the selected skill "
        "declares; derive it from that skill's output-constraints section, not "
        "from the generic workflow. Before writing your final message, confirm: "
        "(1) output_dir/html/<seq>.html exists and is non-empty; "
        "(2) output_dir/png/<seq>.png exists, is non-empty, and you have looked "
        "at it; (3) every companion artifact the selected skill declares exists "
        "at the declared path with the same <seq>, is non-empty, and every "
        "validator script that skill names returned \"valid\": true. Run "
        "`ls -lR <output_dir>` and check all three. Returning only html/ and "
        "png/ while the selected skill declares a companion is a failed run: "
        "create the missing file first, and if you truly cannot, say which file "
        "is missing instead of reporting success.\n"
    )


def _create_backend():
    return build_backend(prefer_shell=True)


def _create_agent():
    if os.getenv("HTML_IMAGE_RENDERER_TEST_MODE") == "1":
        return {
            "name": AGENT_NAME,
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

    model = build_chat_model_for_agent(WORKSPACE_ROOT, AGENT_NAME, timeout=300)
    backend = _create_backend()

    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[],
        skills=[mirror_skills_into_backend(backend, SKILLS_DIR)],
        middleware=[
            make_runtime_context_middleware(lambda: _runtime_context_prompt(cfg)),
            _make_tool_error_middleware(),
        ],
        backend=backend,
        name=AGENT_NAME,
    )


try:
    graph = _create_agent()
except Exception as exc:
    raise RuntimeError(
        f"Failed to initialise html_image_renderer agent: {exc}\n"
        "Check root tool-concurrency.yaml, model-routing.yaml, .env, and installed packages."
    ) from exc
