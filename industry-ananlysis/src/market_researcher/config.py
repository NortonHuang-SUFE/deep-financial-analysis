"""Configuration loader for Market Researcher.

Merge order (highest priority last overrides):
  config.yaml  <  .env / process environment

`config.yaml` and `.env` are resolved from the project root by default, so the
agent uses the same config whether it is launched from this directory or from a
parent workspace.
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


# ── Sub-models ────────────────────────────────────────────────────────────────


class ModelConfig(BaseModel):
    default: str = "MiniMax-M2.7"
    max_tokens: int = 16000
    base_url: str = "https://api.minimaxi.com"
    api_key: str = ""
    thinking: Literal["auto", "enabled", "disabled"] = "auto"


class MCPServerConfig(BaseModel):
    url: str = ""
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"
    token: str = ""
    # Full headers dict — takes priority over token when both are set.
    # Use this when your MCP server needs a raw Authorization value (not Bearer).
    headers: Dict[str, str] = Field(default_factory=dict)


class SearchConfig(BaseModel):
    provider: Literal["tavily", "serper", "duckduckgo", "ifind-news", "none"] = "tavily"
    api_key: str = ""
    max_results: int = 5
    # ifind-news MCP 搜索配置
    ifind_news_url: str = ""
    ifind_news_transport: str = "streamable_http"
    ifind_news_headers: Dict[str, str] = Field(default_factory=dict)


class OutputConfig(BaseModel):
    dir: str = "./out"
    pptx_template: str = "./templates/firm-template.pptx"


# ── Root config ───────────────────────────────────────────────────────────────


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    mcp: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    search: SearchConfig = Field(default_factory=SearchConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def _from_yaml(cls, path: str = "config.yaml") -> "Config":
        config_path = _resolve_project_path(path)
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            # Convert nested mcp dict entries to MCPServerConfig objects
            if "mcp" in data and isinstance(data["mcp"], dict):
                data["mcp"] = {
                    k: MCPServerConfig(**v) if isinstance(v, dict) else v
                    for k, v in data["mcp"].items()
                }
            return cls(**data)
        return cls()

    @classmethod
    def load(cls, config_yaml_path: str = "config.yaml") -> "Config":
        """Load config from YAML and apply environment variable overrides."""
        try:
            from dotenv import load_dotenv

            load_dotenv(PROJECT_ROOT / ".env")
            load_dotenv()
        except ImportError:
            pass

        cfg = cls._from_yaml(config_yaml_path)

        # Model overrides
        cfg.model.default = os.getenv("MODEL_NAME") or cfg.model.default
        cfg.model.base_url = os.getenv("MODEL_BASE_URL") or cfg.model.base_url
        cfg.model.api_key = os.getenv("MODEL_API_KEY") or cfg.model.api_key
        cfg.model.thinking = os.getenv("MODEL_THINKING") or cfg.model.thinking
        model_max_tokens = os.getenv("MODEL_MAX_TOKENS")
        if model_max_tokens:
            cfg.model.max_tokens = int(model_max_tokens)

        if not cfg.model.api_key:
            for env_name in _model_api_key_env_names(cfg.model.base_url):
                cfg.model.api_key = os.getenv(env_name) or ""
                if cfg.model.api_key:
                    break

        # MCP overrides
        for server_name in list(cfg.mcp.keys()):
            server_cfg = cfg.mcp[server_name]
            for prefix in _server_env_prefixes(server_name):
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

        # Search API key override
        if not cfg.search.api_key:
            if cfg.search.provider == "tavily":
                cfg.search.api_key = os.getenv("TAVILY_API_KEY") or ""
            elif cfg.search.provider == "serper":
                cfg.search.api_key = os.getenv("SERPER_API_KEY") or ""

        return cfg


def load_config(path: str = "config.yaml") -> Config:
    """Convenience wrapper used by graph.py and tools.py."""
    return Config.load(path)


def _resolve_project_path(path: str) -> Path:
    """Resolve config-like paths from cwd first, then from this project root."""
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate


def _model_api_key_env_names(base_url: str) -> list[str]:
    """Return env vars for the configured approved model gateway."""
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


def _server_env_prefixes(server_name: str) -> list[str]:
    """Return supported env prefixes for an MCP server name.

    Server names in config.yaml commonly contain hyphens, but shell env vars are
    much easier to work with using underscores. Keep the raw form as a fallback
    for callers that inject environment variables programmatically.
    """
    normalized = "".join(
        char if char.isalnum() else "_" for char in server_name.upper()
    )
    raw = server_name.upper()
    return [normalized] if normalized == raw else [normalized, raw]
