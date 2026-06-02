"""Configuration loader for DCF Builder.

Merge order:
  config.yaml < .env / process environment

Default config paths are resolved from the DCF-builder project root, so graph
loading works the same from this directory or from a parent workspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent


class ModelProfile(BaseModel):
    name: str
    max_tokens: int | None = None
    thinking: Literal["auto", "enabled", "disabled"] | None = None


class ModelConfig(BaseModel):
    active: str = "default"
    default: str = "MiniMax-M2.7"
    max_tokens: int = 16000
    base_url: str = "https://api.minimaxi.com"
    api_key: str = ""
    thinking: Literal["auto", "enabled", "disabled"] = "auto"
    profiles: Dict[str, ModelProfile] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    url: str = ""
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"
    token: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)


class SearchConfig(BaseModel):
    provider: Literal["tavily", "serper", "duckduckgo", "ifind-news", "none"] = "none"
    api_key: str = ""
    max_results: int = 5
    ifind_news_url: str = ""
    ifind_news_transport: str = "streamable_http"
    ifind_news_headers: Dict[str, str] = Field(default_factory=dict)


class OutputConfig(BaseModel):
    dir: str = "./out"


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    mcp: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    search: SearchConfig = Field(default_factory=SearchConfig)
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

            load_dotenv(PROJECT_ROOT / ".env")
            load_dotenv()
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

        if os.getenv("DCF_BUILDER_DISABLE_MCP") == "1":
            for server in cfg.mcp.values():
                server.url = ""

        for server_name in list(cfg.mcp.keys()):
            server_cfg = cfg.mcp[server_name]
            if server_name.startswith("ifind-"):
                shared_auth = os.getenv("IFIND_MCP_AUTHORIZATION")
                shared_token = os.getenv("IFIND_MCP_TOKEN")
                if shared_auth:
                    server_cfg.headers["Authorization"] = shared_auth
                elif shared_token:
                    server_cfg.token = shared_token
                    server_cfg.headers.pop("Authorization", None)

            prefix = _env_slug(server_name)
            url_val = os.getenv(f"{prefix}_MCP_URL")
            if url_val:
                server_cfg.url = url_val

            transport_val = os.getenv(f"{prefix}_MCP_TRANSPORT")
            if transport_val:
                server_cfg.transport = transport_val

            auth_val = os.getenv(f"{prefix}_MCP_AUTHORIZATION")
            if auth_val:
                server_cfg.headers["Authorization"] = auth_val

            token_val = os.getenv(f"{prefix}_MCP_TOKEN")
            if token_val:
                server_cfg.token = token_val
                if not auth_val:
                    server_cfg.headers.pop("Authorization", None)

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


def enabled_mcp_server_configs(cfg: Config) -> dict[str, dict]:
    """Return MultiServerMCPClient-ready server configs."""
    server_configs: dict[str, dict] = {}
    for name, srv in cfg.mcp.items():
        if not srv.url:
            continue
        entry: dict = {
            "url": srv.url.rstrip("/"),
            "transport": srv.transport,
        }
        if srv.headers:
            entry["headers"] = dict(srv.headers)
        elif srv.token:
            entry["headers"] = {"Authorization": f"Bearer {srv.token}"}
        server_configs[name] = entry
    return server_configs


def _env_slug(server_name: str) -> str:
    return server_name.upper().replace("-", "_")


def _model_api_key_env_names(base_url: str) -> list[str]:
    host = urlparse(base_url).netloc.lower()
    if host.endswith("babelark.com"):
        return ["BABELARK_API_KEY"]
    if host.endswith("minimaxi.com") or host.endswith("minimax.io"):
        return ["MINIMAX_API_KEY"]
    if host.endswith("deepseek.com"):
        return ["DEEPSEEK_API_KEY"]
    if host.endswith("dashscope.aliyuncs.com"):
        return ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"]
    return []
