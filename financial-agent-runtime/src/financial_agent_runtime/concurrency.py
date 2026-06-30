"""Process-wide concurrency limiting for external tools (e.g. 同花顺 / iFinD).

Each *group* in the dedicated config file (``tool-concurrency.yaml``) is a shared
concurrency budget. A tool joins a group by matching either an MCP server-name
glob (recorded at tool-load time, since MCP tool names are only known at runtime)
or a tool-name glob (resolved on the fly, e.g. for ``web_search``). When a
group's in-flight calls reach its ``max_concurrency``, further calls block until a
slot frees — serializing execution beyond the threshold.

The semaphores live in module globals, so a single limit holds **process-wide**
across every agent and subagent in the same process — which is what protects an
external service when the orchestrator fans out to many subagents concurrently.
A ``threading.BoundedSemaphore`` (rather than ``asyncio.Semaphore``) is used so
the guarantee is independent of how many event loops/threads the runtime spins
up; the async path acquires it via ``asyncio.to_thread`` so it never blocks the
event loop.
"""

from __future__ import annotations

import asyncio
import fnmatch
import os
import threading
from pathlib import Path
from typing import Any

import yaml


_CONFIG_ENV_VAR = "TOOL_CONCURRENCY_CONFIG"
_CONFIG_FILENAME = "tool-concurrency.yaml"

# Resolved config path -> {group: {"limit", "mcp_server_globs", "tool_globs"}}.
_CONFIG_CACHE: dict[str, dict[str, dict]] = {}
_CONFIG_LOCK = threading.Lock()

# Tool name -> (group, limit) for MCP tools matched by server at load time.
_REGISTRY: dict[str, tuple[str, int]] = {}
_REGISTRY_LOCK = threading.Lock()

# Group -> BoundedSemaphore, created lazily at the group's configured limit.
_SEMAPHORES: dict[str, threading.BoundedSemaphore] = {}
_SEMAPHORES_LOCK = threading.Lock()


__all__ = [
    "load_tool_concurrency_config",
    "load_and_register_mcp_tools",
    "register_limited_tools",
    "resolve_tool_group",
    "make_concurrency_limit_middleware",
]


def _config_path(workspace_root: Path | str | None) -> Path | None:
    override = os.getenv(_CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    if workspace_root is None:
        return None
    return Path(workspace_root) / _CONFIG_FILENAME


def load_tool_concurrency_config(workspace_root: Path | str | None = None) -> dict[str, dict]:
    """Parse the dedicated concurrency config, cached per resolved path.

    Returns ``{group: {"limit", "mcp_server_globs", "tool_globs"}}``. A missing
    or empty file (or no resolvable path) returns ``{}`` so the feature is a
    no-op when unconfigured.
    """
    path = _config_path(workspace_root)
    if path is None:
        return {}
    key = str(path)
    with _CONFIG_LOCK:
        if key in _CONFIG_CACHE:
            return _CONFIG_CACHE[key]
        groups = _parse_config(path)
        _CONFIG_CACHE[key] = groups
        return groups


def _parse_config(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as exc:  # malformed file -> disable limiting, but be loud
        print(
            f"WARNING: could not parse {path}: {exc}. "
            "Tool concurrency limiting disabled."
        )
        return {}

    groups_raw = (raw or {}).get("groups") or {}
    groups: dict[str, dict] = {}
    for name, spec in groups_raw.items():
        if not isinstance(spec, dict):
            continue
        try:
            limit = int(spec.get("max_concurrency", 0))
        except (TypeError, ValueError):
            limit = 0
        if limit < 1:
            print(
                f"WARNING: concurrency group '{name}' has invalid "
                "max_concurrency (must be >= 1); skipping."
            )
            continue
        groups[name] = {
            "limit": limit,
            "mcp_server_globs": [str(p) for p in (spec.get("mcp_servers") or [])],
            "tool_globs": [str(p) for p in (spec.get("tools") or [])],
        }
    return groups


def _most_restrictive(
    label: str, matches: list[tuple[str, int]]
) -> tuple[str, int] | None:
    if not matches:
        return None
    if len({name for name, _ in matches}) > 1:
        names = ", ".join(sorted({name for name, _ in matches}))
        print(
            f"WARNING: '{label}' matches multiple concurrency groups "
            f"({names}); using the most restrictive."
        )
    # Smallest limit wins; tie-break on group name for determinism.
    return min(matches, key=lambda m: (m[1], m[0]))


def _group_for_server(
    server_name: str, groups: dict[str, dict]
) -> tuple[str, int] | None:
    matches = [
        (name, g["limit"])
        for name, g in groups.items()
        if any(fnmatch.fnmatch(server_name, pat) for pat in g["mcp_server_globs"])
    ]
    return _most_restrictive(server_name, matches)


def _group_for_tool_name(
    tool_name: str, groups: dict[str, dict]
) -> tuple[str, int] | None:
    matches = [
        (name, g["limit"])
        for name, g in groups.items()
        if any(fnmatch.fnmatch(tool_name, pat) for pat in g["tool_globs"])
    ]
    return _most_restrictive(tool_name, matches)


def register_limited_tools(
    tools: list,
    *,
    server_name: str,
    workspace_root: Path | str | None = None,
) -> None:
    """Record ``tool.name -> (group, limit)`` for tools from a matched MCP server.

    No-op if the server matches no group. Tool names are taken from the actual
    loaded tool objects, so we never have to guess an MCP server's tool names.
    """
    groups = load_tool_concurrency_config(workspace_root)
    if not groups:
        return
    match = _group_for_server(server_name, groups)
    if match is None:
        return
    group, limit = match
    with _REGISTRY_LOCK:
        for tool in tools:
            name = getattr(tool, "name", None)
            if not name:
                continue
            existing = _REGISTRY.get(name)
            if existing is not None and existing[1] <= limit:
                continue  # keep the already-more-restrictive entry
            _REGISTRY[name] = (group, limit)


def resolve_tool_group(
    tool_name: str | None, workspace_root: Path | str | None = None
) -> tuple[str, int] | None:
    """Return ``(group, limit)`` for a tool, or ``None`` if it is unlimited.

    Checks the load-time registry (MCP tools matched by server) and the config's
    ``tools`` globs (named local/search tools), and returns the most restrictive
    of any matches.
    """
    if not tool_name:
        return None
    with _REGISTRY_LOCK:
        registered = _REGISTRY.get(tool_name)
    groups = load_tool_concurrency_config(workspace_root)
    by_name = _group_for_tool_name(tool_name, groups) if groups else None
    candidates = [c for c in (registered, by_name) if c is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda m: (m[1], m[0]))


def _semaphore(group: str, limit: int) -> threading.BoundedSemaphore:
    with _SEMAPHORES_LOCK:
        sem = _SEMAPHORES.get(group)
        if sem is None:
            sem = threading.BoundedSemaphore(limit)
            _SEMAPHORES[group] = sem
        return sem


async def load_and_register_mcp_tools(
    server_configs: dict,
    *,
    workspace_root: Path | str | None = None,
) -> list:
    """Load MCP tools per server and register any that match a concurrency group.

    Drop-in replacement for the per-package ``_load_mcp_tools_from_config``: same
    flat-list return shape and the same graceful degradation on missing adapters
    or connection failures. Loading per server is what lets us attribute each
    tool to its server (and therefore to a concurrency group) reliably.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("WARNING: langchain-mcp-adapters not installed. MCP tools disabled.")
        return []

    if not server_configs:
        return []

    try:
        client = MultiServerMCPClient(server_configs)
    except Exception as exc:
        print(f"WARNING: Could not initialise MCP client: {exc}")
        return []

    all_tools: list = []
    for name in server_configs:
        try:
            tools = await client.get_tools(server_name=name)
        except TypeError:
            # Older adapters without the server_name kwarg: per-server client.
            try:
                tools = await MultiServerMCPClient(
                    {name: server_configs[name]}
                ).get_tools()
            except Exception as exc:
                print(f"WARNING: Could not connect to MCP server '{name}': {exc}")
                continue
        except Exception as exc:
            print(f"WARNING: Could not connect to MCP server '{name}': {exc}")
            continue
        register_limited_tools(tools, server_name=name, workspace_root=workspace_root)
        all_tools.extend(tools)
    return all_tools


def _agent_middleware_base() -> Any:
    try:
        from langchain.agents.middleware.types import AgentMiddleware

        return AgentMiddleware
    except Exception:
        from deepagents.middleware.skills import SkillsMiddleware

        return SkillsMiddleware.__mro__[1]


def make_concurrency_limit_middleware(workspace_root: Path | str | None = None):
    """Return an ``AgentMiddleware`` that limits per-group tool concurrency.

    Add this **once** to each agent's (and middleware-bearing subagent's)
    ``middleware=[...]`` list, alongside the existing tool-error middleware. A
    tool that resolves to no group runs unwrapped; a matched tool acquires its
    group's process-wide semaphore for the duration of the call.
    """
    base = _agent_middleware_base()

    class ToolConcurrencyLimitMiddleware(base):
        tools = []

        def wrap_tool_call(self, request, handler):
            match = resolve_tool_group(request.tool_call.get("name"), workspace_root)
            if match is None:
                return handler(request)
            group, limit = match
            with _semaphore(group, limit):
                return handler(request)

        async def awrap_tool_call(self, request, handler):
            match = resolve_tool_group(request.tool_call.get("name"), workspace_root)
            if match is None:
                return await handler(request)
            group, limit = match
            sem = _semaphore(group, limit)
            await asyncio.to_thread(sem.acquire)
            try:
                return await handler(request)
            finally:
                sem.release()

    return ToolConcurrencyLimitMiddleware()
