"""Local artifact tools for the Morning Note agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from financial_agent_runtime import (
    artifact_exists,
    backend_is_daytona,
    contains_task_timestamp_dir,
    ensure_artifact_dir,
    write_text_artifact,
)
from langchain_core.tools import tool

from morning_note_agent.config import file_storage_root, load_config


_TASK_OUTPUT_DIRS: dict[str, tuple[Path, datetime]] = {}
_CACHE_TTL_SECONDS = 15 * 60


def _configured_output_dir() -> str:
    return load_config().output.dir


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    return file_storage_root()


def _resolve_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    return path if path.is_absolute() else _workspace_root() / path


def _ensure_dir(path: Path) -> None:
    ensure_artifact_dir(path)


def _write_text(path: Path, text: str) -> None:
    write_text_artifact(path, text, encoding="utf-8")


def _timestamped_output_dir(output_dir: str | None = None) -> Path:
    base = _resolve_output_dir(output_dir or _configured_output_dir())
    if contains_task_timestamp_dir(base):
        _ensure_dir(base)
        return base

    key = _task_cache_key(base)
    existing = _TASK_OUTPUT_DIRS.get(key)
    if existing:
        existing_path, created_at = existing
        if datetime.now() - created_at < timedelta(seconds=_CACHE_TTL_SECONDS):
            _ensure_dir(existing_path)
            return existing_path

    timestamp = os.getenv("MORNING_NOTE_OUTPUT_TIMESTAMP")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    candidate = base / timestamp
    if os.getenv("MORNING_NOTE_OUTPUT_TIMESTAMP") is None and artifact_exists(candidate):
        suffix = 2
        while artifact_exists(base / f"{timestamp}-{suffix}"):
            suffix += 1
        candidate = base / f"{timestamp}-{suffix}"

    _ensure_dir(candidate)
    _TASK_OUTPUT_DIRS[key] = (candidate, datetime.now())
    return candidate


def _task_cache_key(base: Path) -> str:
    scope = os.getenv("MORNING_NOTE_OUTPUT_SCOPE") or _langgraph_scope()
    return f"{base.resolve()}::{scope}"


def _langgraph_scope() -> str:
    for name in (
        "LANGGRAPH_RUN_ID",
        "LANGGRAPH_THREAD_ID",
        "LANGGRAPH_CHECKPOINT_ID",
        "LANGCHAIN_RUN_ID",
        "RUN_ID",
        "THREAD_ID",
    ):
        value = os.getenv(name)
        if value:
            return f"{name}={value}"
    return "process"


def _slugify(text: str, fallback: str = "morning-note") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text).strip()).strip("-").lower()
    return slug or fallback


def _display_path(path: Path) -> str:
    if backend_is_daytona():
        return str(path)
    return str(path.resolve())


@tool
def create_task_output_dir(output_dir: str | None = None) -> str:
    """Create or return the timestamped artifact directory for this task.

    Args:
        output_dir: Optional base output directory. Relative paths are resolved
            from the shared file storage root. If the path already contains a
            task timestamp directory, it is used exactly. Defaults to
            root tool-concurrency.yaml agent_configs.morning_note.output.dir.

    Returns:
        Absolute path of the task output directory.
    """
    out_dir = _timestamped_output_dir(output_dir)
    return _display_path(out_dir)


@tool
def write_markdown_report(
    markdown: str,
    filename: str = "morning-note.md",
    output_dir: str | None = None,
) -> str:
    """Write the final Morning Note markdown artifact.

    Args:
        markdown: Full markdown report text.
        filename: Output filename. Unsafe characters are normalized.
        output_dir: Optional base/output directory resolved from the shared file
            storage root. If the path already contains a task timestamp
            directory, write directly into it. Defaults to root tool-concurrency.yaml output.dir.

    Returns:
        Absolute path of the written markdown file.
    """
    out_dir = _timestamped_output_dir(output_dir)
    safe_name = _slugify(Path(filename).stem, "morning-note") + ".md"
    path = out_dir / safe_name
    _write_text(path, markdown)
    return _display_path(path)


@tool
def write_json_artifact(
    data_json: str,
    filename: str = "morning-note-sources.json",
    output_dir: str | None = None,
) -> str:
    """Write a JSON artifact such as source logs, calendars, or data snapshots.

    Args:
        data_json: Valid JSON string to pretty-print and persist.
        filename: Output filename. Unsafe characters are normalized.
        output_dir: Optional base/output directory resolved from the shared file
            storage root. If the path already contains a task timestamp
            directory, write directly into it. Defaults to root tool-concurrency.yaml output.dir.

    Returns:
        Absolute path of the written JSON file.
    """
    try:
        data: Any = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"data_json must be valid JSON: {exc}") from exc

    out_dir = _timestamped_output_dir(output_dir)
    safe_name = _slugify(Path(filename).stem, "artifact") + ".json"
    path = out_dir / safe_name
    _write_text(
        path,
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    )
    return _display_path(path)
