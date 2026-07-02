"""Configuration loader for the HTML Image Renderer agent.

Merge order:
  root tool-concurrency.yaml < workspace-root .env < process environment
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from financial_agent_runtime import (
    build_backend as _shared_build_backend,
    file_storage_root as _shared_file_storage_root,
    load_workspace_agent_config,
    mirror_skills_into_backend as _shared_mirror_skills_into_backend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
WORKSPACE_ENV_PATH = WORKSPACE_ROOT / ".env"
AGENT_NAME = "html_image_renderer"


def file_storage_root() -> Path:
    return _shared_file_storage_root(WORKSPACE_ROOT)


def build_backend(*, prefer_shell: bool = True):
    return _shared_build_backend(WORKSPACE_ROOT, prefer_shell=prefer_shell)


def mirror_skills_into_backend(backend, local_dir) -> str:
    return _shared_mirror_skills_into_backend(backend, local_dir, file_storage_root())


class OutputConfig(BaseModel):
    dir: str = "./out"


class Config(BaseModel):
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def _from_yaml(cls, path: str | None = None) -> "Config":
        if path:
            config_path = _resolve_project_path(path)
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = load_workspace_agent_config(WORKSPACE_ROOT, AGENT_NAME)

        return cls(**data)

    @classmethod
    def load(cls, override_path: str | None = None) -> "Config":
        try:
            from dotenv import load_dotenv

            load_dotenv(WORKSPACE_ENV_PATH, override=False)
        except ImportError:
            pass

        cfg = cls._from_yaml(override_path)

        cfg.output.dir = os.getenv("HTML_IMAGE_RENDERER_OUTPUT_DIR") or cfg.output.dir
        return cfg


def load_config(path: str | None = None) -> Config:
    return Config.load(path)


def resolve_output_base(output_dir: str) -> Path:
    """Resolve the configured output base from the shared artifact root."""
    path = Path(output_dir)
    return path.resolve() if path.is_absolute() else (file_storage_root() / path).resolve()


def _resolve_project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate
