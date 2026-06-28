"""Local artifact tools for the Thesis Tracker agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
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

from thesis_tracker_agent.config import file_storage_root


_TASK_OUTPUT_DIRS: dict[str, Path] = {}


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


def _timestamped_output_dir(output_dir: str = "./out") -> Path:
    base = _resolve_output_dir(output_dir)
    if contains_task_timestamp_dir(base):
        _ensure_dir(base)
        return base

    key = str(base.resolve())
    existing = _TASK_OUTPUT_DIRS.get(key)
    if existing:
        _ensure_dir(existing)
        return existing

    timestamp = os.getenv("THESIS_TRACKER_OUTPUT_TIMESTAMP")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    candidate = base / timestamp
    if artifact_exists(candidate) and os.getenv("THESIS_TRACKER_OUTPUT_TIMESTAMP") is None:
        suffix = 2
        while artifact_exists(base / f"{timestamp}-{suffix}"):
            suffix += 1
        candidate = base / f"{timestamp}-{suffix}"

    _ensure_dir(candidate)
    _TASK_OUTPUT_DIRS[key] = candidate
    return candidate


def _slugify(text: str, fallback: str = "artifact") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text).strip()).strip("-").lower()
    return slug or fallback


def _relative_to_workspace(path: Path) -> str:
    try:
        return str(path.relative_to(_workspace_root()))
    except ValueError:
        return str(path)


@tool
def create_task_output_dir(output_dir: str = "./out") -> str:
    """Create or return this task's timestamped output directory.

    Args:
        output_dir: Base output directory. Relative paths resolve from the
            workspace root. If the path already contains a task timestamp
            directory, it is used exactly. Defaults to ./out.

    Returns:
        Workspace-relative path to the timestamped output directory.
    """
    return _relative_to_workspace(_timestamped_output_dir(output_dir))


@tool
def write_markdown_report(
    title: str,
    markdown: str,
    filename: str = "",
    output_dir: str = "./out",
) -> str:
    """Write a markdown thesis report into the task output directory.

    Args:
        title: Report title, used for the filename when filename is omitted.
        markdown: Complete markdown report content.
        filename: Optional .md filename.
        output_dir: Base/output directory. Relative paths resolve from the
            workspace root. If the path already contains a task timestamp
            directory, write directly into it. Defaults to ./out.

    Returns:
        Workspace-relative path to the written markdown file.
    """
    out_dir = _timestamped_output_dir(output_dir)
    safe_name = filename or f"{_slugify(title, 'thesis-report')}.md"
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    path = out_dir / _slugify(safe_name, "thesis-report.md")
    _write_text(path, markdown)
    return _relative_to_workspace(path)


@tool
def write_json_artifact(
    data_json: str,
    filename: str = "thesis-artifact.json",
    output_dir: str = "./out",
) -> str:
    """Write a structured JSON artifact into the task output directory.

    Args:
        data_json: Valid JSON string to persist.
        filename: Optional .json filename.
        output_dir: Base/output directory. Relative paths resolve from the
            workspace root. If the path already contains a task timestamp
            directory, write directly into it. Defaults to ./out.

    Returns:
        Workspace-relative path to the written JSON file.
    """
    data: Any = json.loads(data_json)
    out_dir = _timestamped_output_dir(output_dir)
    safe_name = filename if filename.endswith(".json") else f"{filename}.json"
    path = out_dir / _slugify(safe_name, "thesis-artifact.json")
    _write_text(
        path,
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
    )
    return _relative_to_workspace(path)
