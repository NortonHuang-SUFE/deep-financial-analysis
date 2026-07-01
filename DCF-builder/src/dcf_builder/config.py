"""Configuration loader for DCF Builder.

Merge order:
  config.yaml < workspace .env / process environment

Default config paths are resolved from the DCF-builder project root, so graph
loading works the same from this directory or from a parent workspace.
Secrets are read from the parent workspace `.env`, not from project config.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field

from financial_agent_runtime import (
    MCPServerConfig,
    MCPToolGroupConfig,
    apply_mcp_env_overrides,
    build_backend as _shared_build_backend,
    enabled_mcp_server_configs as _shared_enabled_mcp_server_configs,
    file_storage_root as _shared_file_storage_root,
    ifind_auth_headers as _shared_ifind_auth_headers,
    mcp_servers_from_yaml_data,
    mirror_skills_into_backend as _shared_mirror_skills_into_backend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
WORKSPACE_ENV_PATH = WORKSPACE_ROOT / ".env"
DCF_BUILDER_MCP_TOOL_GROUP = "dcf_builder"
ASSUMPTION_RESEARCHER_MCP_TOOL_GROUP = "assumption_researcher"
DEFAULT_ASSUMPTION_MCP_SERVER_NAMES = (
    "ifind-stock",
    "ifind-edb",
    "ifind-news",
    "ifind-index",
    "mx-ds-mcp",
)


def file_storage_root() -> Path:
    return _shared_file_storage_root(WORKSPACE_ROOT)


def build_backend(*, prefer_shell: bool = True):
    return _shared_build_backend(WORKSPACE_ROOT, prefer_shell=prefer_shell)


def mirror_skills_into_backend(backend, local_dir) -> str:
    return _shared_mirror_skills_into_backend(backend, local_dir, file_storage_root())


class ModelProfile(BaseModel):
    name: str
    max_tokens: int | None = None
    thinking: Literal["auto", "enabled", "disabled"] | None = None


class ModelConfig(BaseModel):
    active: str = "qwen"
    default: str = "qwen-3.7-max"
    max_tokens: int = 16000
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode"
    api_key: str = ""
    thinking: Literal["auto", "enabled", "disabled"] = "auto"
    profiles: Dict[str, ModelProfile] = Field(default_factory=dict)


class SearchConfig(BaseModel):
    provider: Literal["tavily", "serper", "duckduckgo", "ifind-news", "none"] = "none"
    api_key: str = ""
    max_results: int = 5
    ifind_news_url: str = ""
    ifind_news_transport: str = "streamable_http"


class OutputConfig(BaseModel):
    dir: str = "./out"


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    mcp: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    mcp_tool_groups: Dict[str, MCPToolGroupConfig] = Field(
        default_factory=lambda: {
            DCF_BUILDER_MCP_TOOL_GROUP: MCPToolGroupConfig(servers="enabled"),
            ASSUMPTION_RESEARCHER_MCP_TOOL_GROUP: MCPToolGroupConfig(
                servers=list(DEFAULT_ASSUMPTION_MCP_SERVER_NAMES)
            ),
        }
    )
    search: SearchConfig = Field(default_factory=SearchConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def _from_yaml(cls, path: str = "config.yaml") -> "Config":
        config_path = _resolve_project_path(path)
        if not config_path.exists():
            return cls()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        mcp_servers = mcp_servers_from_yaml_data(data)
        if mcp_servers is not None:
            data["mcp"] = {
                name: MCPServerConfig(**value) if isinstance(value, dict) else value
                for name, value in mcp_servers.items()
            }
        return cls(**data)

    @classmethod
    def load(cls, config_yaml_path: str = "config.yaml") -> "Config":
        try:
            from dotenv import load_dotenv

            load_dotenv(WORKSPACE_ENV_PATH, override=False)
        except ImportError:
            pass

        cfg = cls._from_yaml(config_yaml_path)

        cfg.model.active = os.getenv("MODEL_PROFILE") or cfg.model.active
        _apply_model_profile(cfg.model)

        cfg.model.default = os.getenv("MODEL_NAME") or cfg.model.default
        cfg.model.base_url = (
            os.getenv("MODEL_GATEWAY_BASE_URL")
            or os.getenv("MODEL_RELAY_BASE_URL")
            or os.getenv("MODEL_BASE_URL")
            or cfg.model.base_url
        )
        cfg.model.api_key = (
            os.getenv("MODEL_GATEWAY_API_KEY")
            or os.getenv("MODEL_RELAY_API_KEY")
            or os.getenv("MODEL_API_KEY")
            or cfg.model.api_key
        )
        cfg.model.thinking = os.getenv("MODEL_THINKING") or cfg.model.thinking
        model_max_tokens = os.getenv("MODEL_MAX_TOKENS")
        if model_max_tokens:
            cfg.model.max_tokens = int(model_max_tokens)

        if not cfg.model.api_key:
            for env_name in _model_api_key_env_names(cfg.model.base_url):
                cfg.model.api_key = os.getenv(env_name) or ""
                if cfg.model.api_key:
                    break

        apply_mcp_env_overrides(
            cfg.mcp,
            disable_env_var="DCF_BUILDER_DISABLE_MCP",
        )

        if not cfg.search.api_key:
            if cfg.search.provider == "tavily":
                cfg.search.api_key = os.getenv("TAVILY_API_KEY") or ""
            elif cfg.search.provider == "serper":
                cfg.search.api_key = os.getenv("SERPER_API_KEY") or ""

        return cfg


def load_config(path: str = "config.yaml") -> Config:
    return Config.load(path)


def _resolve_project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate


def _apply_model_profile(model: ModelConfig) -> None:
    profile_name = (model.active or "").strip()
    if not profile_name:
        return

    profile = model.profiles.get(profile_name)
    if profile is None:
        if profile_name != "default":
            model.default = profile_name
        return

    model.default = profile.name
    if profile.max_tokens is not None:
        model.max_tokens = profile.max_tokens
    if profile.thinking is not None:
        model.thinking = profile.thinking


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


def _model_api_key_env_names(base_url: str) -> list[str]:
    host = urlparse(base_url).netloc.lower()
    if host.endswith("babelark.com"):
        return ["BABELARK_API_KEY"]
    if host.endswith("minimaxi.com") or host.endswith("minimax.io"):
        return ["MINIMAX_API_KEY"]
    if host.endswith("deepseek.com"):
        return ["DEEPSEEK_API_KEY"]
    if host.endswith("volces.com") or host.endswith("volcengineapi.com"):
        return ["ARK_API_KEY", "VOLCENGINE_API_KEY", "VOLCENGINE_ARK_API_KEY"]
    if host.endswith("dashscope.aliyuncs.com"):
        return ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"]
    return []
