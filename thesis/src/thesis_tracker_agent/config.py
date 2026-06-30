"""Configuration loader for the Thesis Tracker agent.

Merge order:
  thesis/config.yaml < workspace-root .env < process environment

The workspace root is the parent of the thesis project directory. This keeps
the agent aligned with the repo-level .env used by langgraph.json.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field

from financial_agent_runtime import (
    build_backend as _shared_build_backend,
    file_storage_root as _shared_file_storage_root,
    mirror_skills_into_backend as _shared_mirror_skills_into_backend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
WORKSPACE_ENV_PATH = WORKSPACE_ROOT / ".env"


def file_storage_root() -> Path:
    return _shared_file_storage_root(WORKSPACE_ROOT)


def build_backend(*, prefer_shell: bool = True):
    return _shared_build_backend(WORKSPACE_ROOT, prefer_shell=prefer_shell)


def mirror_skills_into_backend(backend, local_dir) -> str:
    return _shared_mirror_skills_into_backend(backend, local_dir, file_storage_root())


class ModelConfig(BaseModel):
    default: str = "qwen-3.7-max"
    max_tokens: int = 16000
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode"
    api_key: str = ""
    thinking: Literal["auto", "enabled", "disabled"] = "auto"


class MCPServerConfig(BaseModel):
    url: str = ""
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"


class OutputConfig(BaseModel):
    dir: str = "./out"


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    mcp: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def _from_yaml(cls, path: str = "config.yaml") -> "Config":
        config_path = _resolve_project_path(path)
        if not config_path.exists():
            return cls()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if "mcp" in data and isinstance(data["mcp"], dict):
            data["mcp"] = {
                name: MCPServerConfig(**value) if isinstance(value, dict) else value
                for name, value in data["mcp"].items()
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

        if os.getenv("THESIS_TRACKER_DISABLE_MCP") == "1":
            for server in cfg.mcp.values():
                server.url = ""

        for server_name, server_cfg in cfg.mcp.items():
            prefix = _env_slug(server_name)
            url_val = os.getenv(f"{prefix}_MCP_URL")
            if url_val:
                server_cfg.url = url_val

            transport_val = os.getenv(f"{prefix}_MCP_TRANSPORT")
            if transport_val:
                server_cfg.transport = transport_val

        return cfg


def load_config(path: str = "config.yaml") -> Config:
    return Config.load(path)


def enabled_mcp_server_configs(cfg: Config) -> dict[str, dict]:
    server_configs: dict[str, dict] = {}
    for name, srv in cfg.mcp.items():
        if not srv.url:
            continue
        entry: dict = {
            "url": srv.url.rstrip("/"),
            "transport": srv.transport,
        }
        if name.startswith("ifind-"):
            headers = ifind_auth_headers()
            if headers:
                entry["headers"] = headers
        server_configs[name] = entry
    return server_configs


def ifind_auth_headers() -> dict[str, str]:
    """Return the shared iFind MCP Authorization header from environment."""
    shared_auth = os.getenv("IFIND_MCP_AUTHORIZATION")
    if shared_auth:
        return {"Authorization": shared_auth}
    shared_token = os.getenv("IFIND_MCP_TOKEN")
    if shared_token:
        return {"Authorization": f"Bearer {shared_token}"}
    return {}


def _resolve_project_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate


def _env_slug(server_name: str) -> str:
    return server_name.upper().replace("-", "_")


def _model_api_key_env_names(base_url: str) -> list[str]:
    host = urlparse(base_url).netloc.lower()
    if host.endswith("dashscope.aliyuncs.com"):
        return ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"]
    if host.endswith("babelark.com"):
        return ["BABELARK_API_KEY"]
    if host.endswith("minimaxi.com") or host.endswith("minimax.io"):
        return ["MINIMAX_API_KEY"]
    if host.endswith("deepseek.com"):
        return ["DEEPSEEK_API_KEY"]
    if host.endswith("volces.com") or host.endswith("volcengineapi.com"):
        return ["ARK_API_KEY", "VOLCENGINE_API_KEY", "VOLCENGINE_ARK_API_KEY"]
    return []
