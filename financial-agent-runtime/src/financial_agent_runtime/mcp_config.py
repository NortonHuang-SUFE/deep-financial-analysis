"""Shared MCP configuration helpers for workspace agents."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MX_DS_MCP_SERVER_NAME = "mx-ds-mcp"
MX_DS_MCP_URL = "https://mxapi.eastmoney.com/mxds/mcp"


class MCPServerConfig(BaseModel):
    """One server entry from a project's ``mcp`` config section."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    url: str = ""
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"
    headers: dict[str, str] = Field(default_factory=dict)
    connect_timeout: int | None = Field(default=None, alias="connectTimeout")
    timeout: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_transport(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        transport = normalized.get("transport")
        if isinstance(transport, str):
            normalized["transport"] = transport.replace("-", "_")
        return normalized


class MCPToolGroupConfig(BaseModel):
    """Server allowlist for a runtime MCP tool group."""

    model_config = ConfigDict(extra="allow")

    servers: str | list[str] | None = "enabled"


def default_mcp_tool_groups() -> dict[str, MCPToolGroupConfig]:
    return {"default": MCPToolGroupConfig(servers="enabled")}


def mcp_servers_from_yaml_data(data: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the MCP server mapping from either supported YAML shape."""

    mcp = data.get("mcp")
    if not isinstance(mcp, dict):
        return None
    servers = mcp.get("servers")
    if isinstance(servers, dict):
        return servers
    return mcp


def apply_mcp_env_overrides(
    mcp: Mapping[str, MCPServerConfig],
    *,
    disable_env_var: str | None = None,
) -> None:
    """Apply env URL/transport/header overrides in-place."""

    if disable_env_var and os.getenv(disable_env_var) == "1":
        for server in mcp.values():
            server.url = ""

    for server_name, server_cfg in mcp.items():
        url_val = _first_env_value(_mcp_server_env_names(server_name, "URL"))
        if url_val:
            server_cfg.url = url_val

        transport_val = _first_env_value(
            _mcp_server_env_names(server_name, "TRANSPORT")
        )
        if transport_val:
            server_cfg.transport = transport_val.replace("-", "_")

        server_cfg.headers = _headers_with_env_overrides(
            server_name,
            server_cfg.headers,
        )


def enabled_mcp_server_configs(
    cfg_or_mcp: Any,
    *,
    server_names: set[str] | None = None,
) -> dict[str, dict]:
    """Return MultiServerMCPClient-ready configs for enabled MCP servers."""

    mcp = getattr(cfg_or_mcp, "mcp", cfg_or_mcp)
    server_configs: dict[str, dict] = {}
    for name, srv in mcp.items():
        if not srv.url:
            continue
        if server_names is not None and name not in server_names:
            continue
        entry: dict[str, Any] = {
            "url": srv.url.rstrip("/"),
            "transport": srv.transport,
        }
        if srv.headers:
            headers = {key: value for key, value in srv.headers.items() if value}
            if headers:
                entry["headers"] = headers
        if srv.timeout is not None:
            entry["timeout"] = srv.timeout
        elif srv.connect_timeout is not None:
            entry["timeout"] = srv.connect_timeout
        server_configs[name] = entry
    return server_configs


def mcp_tool_group_server_names(
    tool_groups: Mapping[str, Any] | None,
    group_name: str,
    all_server_names: Sequence[str],
    *,
    default_servers: str | Sequence[str] | None = "enabled",
) -> set[str]:
    """Resolve server-name globs for a configured MCP tool group."""

    group = (tool_groups or {}).get(group_name) if tool_groups else None
    servers = getattr(group, "servers", None)
    if servers is None and isinstance(group, Mapping):
        servers = group.get("servers")
    if servers is None:
        servers = default_servers
    return mcp_server_names_from_patterns(servers, all_server_names)


def mcp_server_names_from_patterns(
    patterns: str | Sequence[str] | None,
    all_server_names: Sequence[str],
) -> set[str]:
    if patterns in (None, "enabled"):
        return set(all_server_names)
    if isinstance(patterns, str):
        pattern_list = [patterns]
    else:
        pattern_list = [str(pattern) for pattern in patterns]
    return {
        server_name
        for server_name in all_server_names
        if any(fnmatch.fnmatch(server_name, pattern) for pattern in pattern_list)
    }


def ifind_auth_headers() -> dict[str, str]:
    shared_auth = os.getenv("IFIND_MCP_AUTHORIZATION")
    if shared_auth:
        return {"Authorization": shared_auth}
    shared_token = os.getenv("IFIND_MCP_TOKEN")
    if shared_token:
        return {"Authorization": f"Bearer {shared_token}"}
    return {}


def mx_ds_auth_headers() -> dict[str, str]:
    api_key = (
        os.getenv("MX_DS_MCP_API_KEY")
        or os.getenv("MX_DS_MCP_EM_API_KEY")
        or os.getenv("EASTMONEY_MX_DS_MCP_API_KEY")
        or ""
    )
    if api_key:
        return {"em_api_key": api_key}
    return {}


def _headers_with_env_overrides(
    server_name: str,
    headers: Mapping[str, str],
) -> dict[str, str]:
    resolved = {
        key: _expand_env_reference(str(value))
        for key, value in dict(headers or {}).items()
    }
    if server_name.startswith("ifind-"):
        resolved.update(ifind_auth_headers())
    if server_name == MX_DS_MCP_SERVER_NAME:
        resolved.update(mx_ds_auth_headers())
    return resolved


def _expand_env_reference(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("${") and stripped.endswith("}"):
        return os.getenv(stripped[2:-1], "")
    if stripped.startswith("$") and len(stripped) > 1:
        return os.getenv(stripped[1:], "")
    return value


def _mcp_server_env_names(server_name: str, suffix: str) -> list[str]:
    normalized = _env_slug(server_name)
    raw = server_name.upper()
    names = [f"{normalized}_MCP_{suffix}"]
    if normalized.endswith("_MCP"):
        names.append(f"{normalized}_{suffix}")
    if raw != normalized:
        names.append(f"{raw}_MCP_{suffix}")
        if raw.endswith("-MCP"):
            names.append(f"{raw}_{suffix}")
    return _dedupe(names)


def _env_slug(server_name: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in server_name.upper())


def _first_env_value(names: Sequence[str]) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
