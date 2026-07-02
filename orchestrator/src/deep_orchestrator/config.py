"""Configuration loader for the Deep Orchestrator agent.

Merge order:
  root tool-concurrency.yaml < workspace-root .env < process environment

The workspace root is the parent of the orchestrator/ project directory.
This keeps the agent aligned with the repo-level .env used by langgraph.json.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from financial_agent_runtime import (
    build_backend as _shared_build_backend,
    file_storage_root as _shared_file_storage_root,
    load_workspace_agent_config,
    mirror_skills_into_backend as _shared_mirror_skills_into_backend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
WORKSPACE_ENV_PATH = WORKSPACE_ROOT / ".env"
AGENT_NAME = "deep_orchestrator"


def file_storage_root() -> Path:
    return _shared_file_storage_root(WORKSPACE_ROOT)


def build_backend(*, prefer_shell: bool = True):
    return _shared_build_backend(WORKSPACE_ROOT, prefer_shell=prefer_shell)


def mirror_skills_into_backend(backend, local_dir) -> str:
    return _shared_mirror_skills_into_backend(backend, local_dir, file_storage_root())


class Config(BaseModel):

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
        return cfg


def load_config(path: str | None = None) -> Config:
    return Config.load(path)


def _resolve_project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate
