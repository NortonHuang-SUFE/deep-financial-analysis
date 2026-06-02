"""Local artifact tools for the Thesis Tracker agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


_TASK_OUTPUT_DIRS: dict[str, Path] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    return _project_root().parent


def _resolve_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    return path if path.is_absolute() else _workspace_root() / path


def _timestamped_output_dir(output_dir: str = "./out") -> Path:
    base = _resolve_output_dir(output_dir)
    if re.fullmatch(r"\d{8}-\d{6}(?:-\d+)?", base.name):
        base.mkdir(parents=True, exist_ok=True)
        return base

    key = str(base.resolve())
    existing = _TASK_OUTPUT_DIRS.get(key)
    if existing:
        existing.mkdir(parents=True, exist_ok=True)
        return existing

    timestamp = os.getenv("THESIS_TRACKER_OUTPUT_TIMESTAMP")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    candidate = base / timestamp
    if candidate.exists() and os.getenv("THESIS_TRACKER_OUTPUT_TIMESTAMP") is None:
        suffix = 2
        while (base / f"{timestamp}-{suffix}").exists():
            suffix += 1
        candidate = base / f"{timestamp}-{suffix}"

    candidate.mkdir(parents=True, exist_ok=True)
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
            workspace root. Defaults to ./out.

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
        output_dir: Base output directory. Relative paths resolve from the
            workspace root. Defaults to ./out.

    Returns:
        Workspace-relative path to the written markdown file.
    """
    out_dir = _timestamped_output_dir(output_dir)
    safe_name = filename or f"{_slugify(title, 'thesis-report')}.md"
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    path = out_dir / _slugify(safe_name, "thesis-report.md")
    path.write_text(markdown, encoding="utf-8")
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
        output_dir: Base output directory. Relative paths resolve from the
            workspace root. Defaults to ./out.

    Returns:
        Workspace-relative path to the written JSON file.
    """
    data: Any = json.loads(data_json)
    out_dir = _timestamped_output_dir(output_dir)
    safe_name = filename if filename.endswith(".json") else f"{filename}.json"
    path = out_dir / _slugify(safe_name, "thesis-artifact.json")
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return _relative_to_workspace(path)
