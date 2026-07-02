"""Configuration loader for Market Researcher.

Merge order (highest priority last overrides):
  root tool-concurrency.yaml < workspace .env / process environment

Runtime defaults are read from the workspace root. Secrets are read from the
parent workspace `.env`, so sibling agents share one credential source.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal

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
AGENT_NAME = "market_researcher"


def file_storage_root() -> Path:
    return _shared_file_storage_root(WORKSPACE_ROOT)


def build_backend(*, prefer_shell: bool = True):
    return _shared_build_backend(WORKSPACE_ROOT, prefer_shell=prefer_shell)


def mirror_skills_into_backend(backend, local_dir) -> str:
    return _shared_mirror_skills_into_backend(backend, local_dir, file_storage_root())


class SearchConfig(BaseModel):
    provider: Literal["tavily", "serper", "duckduckgo", "ifind-news", "none"] = "tavily"
    api_key: str = ""
    max_results: int = 5
    # ifind-news MCP 搜索配置
    ifind_news_url: str = ""
    ifind_news_transport: str = "streamable_http"


class OutputConfig(BaseModel):
    dir: str = "./out"
    pptx_template: str = "./templates/firm-template.pptx"


# ── Root config ───────────────────────────────────────────────────────────────


class Config(BaseModel):
    mcp: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    search: SearchConfig = Field(default_factory=SearchConfig)
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
                k: MCPServerConfig(**v) if isinstance(v, dict) else v
                for k, v in mcp_servers.items()
            }
        return cls(**data)

    @classmethod
    def load(cls, override_path: str | None = None) -> "Config":
        """Load config from YAML and apply environment variable overrides."""
        try:
            from dotenv import load_dotenv

            load_dotenv(WORKSPACE_ENV_PATH, override=False)
        except ImportError:
            pass

        cfg = cls._from_yaml(override_path)

        apply_mcp_env_overrides(cfg.mcp)

        # Search API key override
        if not cfg.search.api_key:
            if cfg.search.provider == "tavily":
                cfg.search.api_key = os.getenv("TAVILY_API_KEY") or ""
            elif cfg.search.provider == "serper":
                cfg.search.api_key = os.getenv("SERPER_API_KEY") or ""

        return cfg


def load_config(path: str | None = None) -> Config:
    """Convenience wrapper used by graph.py and tools.py."""
    return Config.load(path)


def enabled_mcp_server_configs(
    cfg: Config,
    *,
    server_names: set[str] | None = None,
) -> dict[str, dict]:
    """Return MultiServerMCPClient-ready server configs."""
    return _shared_enabled_mcp_server_configs(cfg, server_names=server_names)


def ifind_auth_headers() -> dict[str, str]:
    """Return the shared iFind MCP Authorization header from environment."""
    return _shared_ifind_auth_headers()


def _resolve_project_path(path: str) -> Path:
    """Resolve config-like paths from cwd first, then from this project root."""
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate
