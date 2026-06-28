"""Local artifact tools for the Sector Research Agent."""

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

from sector_research_agent.config import file_storage_root


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

    timestamp = os.getenv("SECTOR_RESEARCH_OUTPUT_TIMESTAMP")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    candidate = base / timestamp
    if artifact_exists(candidate) and os.getenv("SECTOR_RESEARCH_OUTPUT_TIMESTAMP") is None:
        suffix = 2
        while artifact_exists(base / f"{timestamp}-{suffix}"):
            suffix += 1
        candidate = base / f"{timestamp}-{suffix}"

    _ensure_dir(candidate)
    _TASK_OUTPUT_DIRS[key] = candidate
    return candidate


def _safe_filename(name: str, suffix: str) -> str:
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", name.strip(), flags=re.UNICODE)
    stem = stem.strip(".-") or "artifact"
    if not stem.endswith(suffix):
        stem += suffix
    return stem


def _relative_to_workspace(path: Path) -> str:
    try:
        return str(path.relative_to(_workspace_root()))
    except ValueError:
        return str(path)


@tool
def create_task_output_dir(output_dir: str = "./out") -> str:
    """Create or return the current task output directory under workspace out/.

    If output_dir already points inside a task timestamp directory, it is used
    exactly instead of creating another timestamp child.
    """
    out_dir = _timestamped_output_dir(output_dir)
    return _relative_to_workspace(out_dir)


@tool
def write_markdown_report(
    filename: str,
    markdown: str,
    output_dir: str = "./out",
) -> str:
    """Write a Markdown sector research report to the task output directory.

    If output_dir already points inside a task timestamp directory, it is used
    exactly instead of creating another timestamp child.
    """
    out_dir = _timestamped_output_dir(output_dir)
    path = out_dir / _safe_filename(filename, ".md")
    _write_text(path, markdown)
    return _relative_to_workspace(path)


@tool
def write_json_artifact(
    filename: str,
    data_json: str,
    output_dir: str = "./out",
) -> str:
    """Write a JSON artifact after validating that data_json is valid JSON.

    If output_dir already points inside a task timestamp directory, it is used
    exactly instead of creating another timestamp child.
    """
    parsed: Any = json.loads(data_json)
    out_dir = _timestamped_output_dir(output_dir)
    path = out_dir / _safe_filename(filename, ".json")
    _write_text(
        path,
        json.dumps(parsed, ensure_ascii=False, indent=2),
    )
    return _relative_to_workspace(path)
