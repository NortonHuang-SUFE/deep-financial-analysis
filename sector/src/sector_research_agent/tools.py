"""Local artifact tools for the Sector Research Agent."""

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

    timestamp = os.getenv("SECTOR_RESEARCH_OUTPUT_TIMESTAMP")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    candidate = base / timestamp
    if candidate.exists() and os.getenv("SECTOR_RESEARCH_OUTPUT_TIMESTAMP") is None:
        suffix = 2
        while (base / f"{timestamp}-{suffix}").exists():
            suffix += 1
        candidate = base / f"{timestamp}-{suffix}"

    candidate.mkdir(parents=True, exist_ok=True)
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
    """Create or return the current task output directory under workspace out/."""
    out_dir = _timestamped_output_dir(output_dir)
    return _relative_to_workspace(out_dir)


@tool
def write_markdown_report(
    filename: str,
    markdown: str,
    output_dir: str = "./out",
) -> str:
    """Write a Markdown sector research report to the task output directory."""
    out_dir = _timestamped_output_dir(output_dir)
    path = out_dir / _safe_filename(filename, ".md")
    path.write_text(markdown, encoding="utf-8")
    return _relative_to_workspace(path)


@tool
def write_json_artifact(
    filename: str,
    data_json: str,
    output_dir: str = "./out",
) -> str:
    """Write a JSON artifact after validating that data_json is valid JSON."""
    parsed: Any = json.loads(data_json)
    out_dir = _timestamped_output_dir(output_dir)
    path = out_dir / _safe_filename(filename, ".json")
    path.write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return _relative_to_workspace(path)

