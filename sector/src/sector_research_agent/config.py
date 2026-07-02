"""Configuration loader for Sector Research Agent.

Merge order:
  root tool-concurrency.yaml < workspace-root .env < process environment

The project intentionally reads credentials from the parent workspace `.env`
instead of requiring a project-local `.env` file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml
from pydantic import BaseModel, Field

from financial_agent_runtime import (
    MCPServerConfig,
    apply_mcp_env_overrides,
    build_backend as _shared_build_backend,
    enabled_mcp_server_configs as _shared_enabled_mcp_server_configs,
    file_storage_root as _shared_file_storage_root,
    ifind_auth_headers as _shared_ifind_auth_headers,
    load_workspace_agent_config,
    mcp_servers_from_yaml_data,
    mirror_skills_into_backend as _shared_mirror_skills_into_backend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
WORKSPACE_ENV_PATH = WORKSPACE_ROOT / ".env"
AGENT_NAME = "sector_research"


def file_storage_root() -> Path:
    return _shared_file_storage_root(WORKSPACE_ROOT)


def build_backend(*, prefer_shell: bool = True):
    return _shared_build_backend(WORKSPACE_ROOT, prefer_shell=prefer_shell)


def mirror_skills_into_backend(backend, local_dir) -> str:
    return _shared_mirror_skills_into_backend(backend, local_dir, file_storage_root())


class OutputConfig(BaseModel):
    dir: str = "./out"


class Config(BaseModel):
    mcp: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def _from_yaml(cls, path: str | None = None) -> "Config":
        if path:
            config_path = _resolve_project_path(path)
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = load_workspace_agent_config(WORKSPACE_ROOT, AGENT_NAME)

        mcp_servers = mcp_servers_from_yaml_data(data)
        if mcp_servers is not None:
            data["mcp"] = {
                name: MCPServerConfig(**value) if isinstance(value, dict) else value
                for name, value in mcp_servers.items()
            }
        return cls(**data)

    @classmethod
    def load(cls, override_path: str | None = None) -> "Config":
        try:
            from dotenv import load_dotenv

            load_dotenv(WORKSPACE_ENV_PATH)
        except ImportError:
            pass

        cfg = cls._from_yaml(override_path)

        apply_mcp_env_overrides(
            cfg.mcp,
            disable_env_var="SECTOR_RESEARCH_DISABLE_MCP",
        )

        return cfg


def load_config(path: str | None = None) -> Config:
    return Config.load(path)


def enabled_mcp_server_configs(
    cfg: Config,
    *,
    server_names: set[str] | None = None,
) -> dict[str, dict]:
    return _shared_enabled_mcp_server_configs(cfg, server_names=server_names)


def ifind_auth_headers() -> dict[str, str]:
    return _shared_ifind_auth_headers()


def _resolve_project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate
