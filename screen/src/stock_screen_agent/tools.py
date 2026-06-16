"""Local artifact tools for the stock screen agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from stock_screen_agent.config import file_storage_root


_TASK_OUTPUT_DIRS: dict[str, Path] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    return file_storage_root()


def _resolve_output_dir(output_dir: str = "./out") -> Path:
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

    timestamp = os.getenv("STOCK_SCREEN_OUTPUT_TIMESTAMP")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    candidate = base / timestamp
    if candidate.exists() and os.getenv("STOCK_SCREEN_OUTPUT_TIMESTAMP") is None:
        suffix = 2
        while (base / f"{timestamp}-{suffix}").exists():
            suffix += 1
        candidate = base / f"{timestamp}-{suffix}"

    candidate.mkdir(parents=True, exist_ok=True)
    _TASK_OUTPUT_DIRS[key] = candidate
    return candidate


def _slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text).strip()).strip("-").lower()
    return slug or fallback


def _relative_to_workspace(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_workspace_root()))
    except ValueError:
        return str(path.resolve())


@tool
def create_task_output_dir(output_dir: str = "./out") -> str:
    """Create or return the current task's timestamped output directory.

    The directory is written under the workspace root by default:
    out/<YYYYMMDD-HHMMSS>/. Set STOCK_SCREEN_OUTPUT_TIMESTAMP to force a stable
    timestamp during tests or reproducible runs.
    """
    return _relative_to_workspace(_timestamped_output_dir(output_dir))


@tool
def write_markdown_report(
    markdown: str,
    filename: str = "stock-screen-report.md",
    output_dir: str = "./out",
) -> str:
    """Write a markdown stock screening report into the task output directory."""
    out_dir = _timestamped_output_dir(output_dir)
    safe_name = _slugify(filename, "stock-screen-report.md")
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    path = out_dir / safe_name
    path.write_text(markdown, encoding="utf-8")
    return _relative_to_workspace(path)


@tool
def write_json_artifact(
    data_json: str,
    filename: str = "stock-screen-artifact.json",
    output_dir: str = "./out",
) -> str:
    """Validate and write a JSON artifact into the task output directory."""
    try:
        data: Any = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"data_json must be valid JSON: {exc}") from exc

    out_dir = _timestamped_output_dir(output_dir)
    safe_name = _slugify(filename, "stock-screen-artifact.json")
    if not safe_name.endswith(".json"):
        safe_name += ".json"
    path = out_dir / safe_name
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return _relative_to_workspace(path)
