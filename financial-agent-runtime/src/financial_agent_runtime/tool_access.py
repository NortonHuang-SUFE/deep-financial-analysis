"""Root-level tool access configuration for workspace agents.

``tool-concurrency.yaml`` owns two independent concerns:

* ``groups``: process-wide concurrency budgets, parsed by ``concurrency.py``.
* ``tool_groups`` / ``agent_tools``: which tools each agent may see, parsed here.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from .mcp_config import mcp_server_names_from_patterns


_CONFIG_ENV_VAR = "TOOL_CONCURRENCY_CONFIG"
_CONFIG_FILENAME = "tool-concurrency.yaml"
_ACCESS_CONFIG_CACHE: dict[str, "ToolAccessConfig"] = {}
_ACCESS_CONFIG_LOCK = threading.Lock()

ToolGroupSource = Literal["local", "mcp", "dynamic"]


@dataclass(frozen=True)
class ToolGroupAccessConfig:
    """One reusable tool group from the root tool config."""

    source: ToolGroupSource
    tools: tuple[str, ...] = ()
    servers: str | tuple[str, ...] | None = None
    description: str = ""


@dataclass(frozen=True)
class AgentToolAccessConfig:
    """Configured tool grants for one agent or subagent."""

    tool_groups: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolAccessConfig:
    """Parsed root tool access config."""

    tool_groups: dict[str, ToolGroupAccessConfig]
    agent_tools: dict[str, AgentToolAccessConfig]


__all__ = [
    "AgentToolAccessConfig",
    "ToolAccessConfig",
    "ToolGroupAccessConfig",
    "build_tool_catalog",
    "describe_agent_tool_access",
    "load_tool_access_config",
    "mcp_server_names_for_tool_group",
    "mcp_tool_group_names_for_agent",
    "resolve_agent_tools",
    "tool_access_config_path",
]


def tool_access_config_path(workspace_root: Path | str | None) -> Path | None:
    override = os.getenv(_CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    if workspace_root is None:
        return None
    return Path(workspace_root) / _CONFIG_FILENAME


def load_tool_access_config(
    workspace_root: Path | str | None = None,
) -> ToolAccessConfig:
    """Parse root-level tool access config from ``tool-concurrency.yaml``."""

    path = tool_access_config_path(workspace_root)
    if path is None:
        return ToolAccessConfig(tool_groups={}, agent_tools={})
    key = str(path)
    with _ACCESS_CONFIG_LOCK:
        if key in _ACCESS_CONFIG_CACHE:
            return _ACCESS_CONFIG_CACHE[key]
        cfg = _parse_tool_access_config(path)
        _ACCESS_CONFIG_CACHE[key] = cfg
        return cfg


def _parse_tool_access_config(path: Path) -> ToolAccessConfig:
    if not path.exists():
        return ToolAccessConfig(tool_groups={}, agent_tools={})
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as exc:
        raise ValueError(f"Could not parse tool access config at {path}: {exc}") from exc

    return ToolAccessConfig(
        tool_groups=_parse_tool_groups(raw.get("tool_groups") or {}),
        agent_tools=_parse_agent_tools(raw.get("agent_tools") or {}),
    )


def _parse_tool_groups(raw_groups: Any) -> dict[str, ToolGroupAccessConfig]:
    if not isinstance(raw_groups, dict):
        raise ValueError("tool_groups must be a mapping")

    groups: dict[str, ToolGroupAccessConfig] = {}
    for name, raw_spec in raw_groups.items():
        if not isinstance(raw_spec, dict):
            raise ValueError(f"tool_groups.{name} must be a mapping")
        source = str(raw_spec.get("source") or "").strip()
        if source not in {"local", "mcp", "dynamic"}:
            raise ValueError(
                f"tool_groups.{name}.source must be one of: local, mcp, dynamic"
            )
        groups[str(name)] = ToolGroupAccessConfig(
            source=source,  # type: ignore[arg-type]
            tools=tuple(_string_list(raw_spec.get("tools"), f"tool_groups.{name}.tools")),
            servers=_servers_value(raw_spec.get("servers")),
            description=str(raw_spec.get("description") or ""),
        )
    return groups


def _parse_agent_tools(raw_agents: Any) -> dict[str, AgentToolAccessConfig]:
    if not isinstance(raw_agents, dict):
        raise ValueError("agent_tools must be a mapping")

    agents: dict[str, AgentToolAccessConfig] = {}
    for name, raw_spec in raw_agents.items():
        if not isinstance(raw_spec, dict):
            raise ValueError(f"agent_tools.{name} must be a mapping")
        agents[str(name)] = AgentToolAccessConfig(
            tool_groups=tuple(
                _string_list(raw_spec.get("tool_groups"), f"agent_tools.{name}.tool_groups")
            ),
            tools=tuple(_string_list(raw_spec.get("tools"), f"agent_tools.{name}.tools")),
        )
    return agents


def _string_list(value: Any, field_name: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")
    return [str(item) for item in value]


def _servers_value(value: Any) -> str | tuple[str, ...] | None:
    if value in (None, ""):
        return None
    if value == "enabled" or isinstance(value, str):
        return str(value)
    if not isinstance(value, list):
        raise ValueError("mcp tool group servers must be 'enabled' or a list")
    return tuple(str(item) for item in value)


def build_tool_catalog(tools: list[Any] | tuple[Any, ...]) -> dict[str, Any]:
    """Return ``tool.name -> tool`` for exact-name tool grants."""

    catalog: dict[str, Any] = {}
    for tool in tools:
        name = getattr(tool, "name", None)
        if not name:
            continue
        if name in catalog and catalog[name] is not tool:
            raise ValueError(f"Duplicate local tool name in catalog: {name}")
        catalog[name] = tool
    return catalog


def resolve_agent_tools(
    agent_name: str,
    *,
    access_config: ToolAccessConfig,
    local_tools: dict[str, Any],
    dynamic_tool_groups: dict[str, list[Any]] | None = None,
    mcp_tool_groups: dict[str, list[Any]] | None = None,
) -> list[Any]:
    """Resolve one agent's configured grants to concrete tool objects."""

    spec = _agent_spec(access_config, agent_name)
    dynamic_tool_groups = dynamic_tool_groups or {}
    mcp_tool_groups = mcp_tool_groups or {}

    resolved: list[Any] = []
    for group_name in spec.tool_groups:
        group = _tool_group(access_config, group_name)
        if group.source == "local":
            resolved.extend(_resolve_named_tools(group.tools, local_tools, group_name))
        elif group.source == "mcp":
            if group_name not in mcp_tool_groups:
                raise KeyError(
                    f"Agent '{agent_name}' uses MCP tool group '{group_name}', "
                    "but that group was not loaded"
                )
            resolved.extend(mcp_tool_groups[group_name])
        elif group.source == "dynamic":
            if group_name not in dynamic_tool_groups:
                raise KeyError(
                    f"Agent '{agent_name}' uses dynamic tool group '{group_name}', "
                    "but that group was not provided"
                )
            resolved.extend(dynamic_tool_groups[group_name])

    resolved.extend(_resolve_named_tools(spec.tools, local_tools, agent_name))
    return _dedupe_tools(resolved)


def describe_agent_tool_access(
    access_config: ToolAccessConfig,
    agent_name: str,
) -> dict[str, Any]:
    """Return a human-readable grant summary for an agent."""

    spec = _agent_spec(access_config, agent_name)
    return {
        "tool_groups": list(spec.tool_groups),
        "direct_tools": list(spec.tools),
        "tools": {
            group_name: _configured_tool_names(access_config, group_name)
            for group_name in spec.tool_groups
        },
    }


def mcp_tool_group_names_for_agent(
    access_config: ToolAccessConfig,
    agent_name: str,
) -> tuple[str, ...]:
    spec = _agent_spec(access_config, agent_name)
    return tuple(
        group_name
        for group_name in spec.tool_groups
        if _tool_group(access_config, group_name).source == "mcp"
    )


def mcp_server_names_for_tool_group(
    access_config: ToolAccessConfig,
    group_name: str,
    all_server_names: list[str],
) -> set[str]:
    group = _tool_group(access_config, group_name)
    if group.source != "mcp":
        raise ValueError(f"Tool group '{group_name}' is not an MCP tool group")
    return mcp_server_names_from_patterns(group.servers or "enabled", all_server_names)


def _agent_spec(
    access_config: ToolAccessConfig,
    agent_name: str,
) -> AgentToolAccessConfig:
    try:
        return access_config.agent_tools[agent_name]
    except KeyError as exc:
        raise KeyError(f"No root tool access config for agent: {agent_name}") from exc


def _tool_group(
    access_config: ToolAccessConfig,
    group_name: str,
) -> ToolGroupAccessConfig:
    try:
        return access_config.tool_groups[group_name]
    except KeyError as exc:
        raise KeyError(f"Unknown root tool group: {group_name}") from exc


def _resolve_named_tools(
    tool_names: tuple[str, ...],
    local_tools: dict[str, Any],
    label: str,
) -> list[Any]:
    tools: list[Any] = []
    for tool_name in tool_names:
        try:
            tools.append(local_tools[tool_name])
        except KeyError as exc:
            raise KeyError(f"Unknown tool '{tool_name}' in {label}") from exc
    return tools


def _configured_tool_names(
    access_config: ToolAccessConfig,
    group_name: str,
) -> list[str]:
    group = _tool_group(access_config, group_name)
    if group.source == "mcp":
        servers = group.servers or "enabled"
        if servers == "enabled":
            return ["<runtime MCP tools from all enabled root mcp_servers>"]
        if isinstance(servers, str):
            servers = (servers,)
        return [f"<runtime MCP tools from {', '.join(servers)}>"]
    if group.source == "dynamic":
        return [f"<runtime dynamic tools for {group_name}>"]
    return list(group.tools)


def _dedupe_tools(tools: list[Any]) -> list[Any]:
    seen: set[tuple[str | None, int]] = set()
    deduped: list[Any] = []
    for tool in tools:
        key = (getattr(tool, "name", None), id(tool))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(tool)
    return deduped
