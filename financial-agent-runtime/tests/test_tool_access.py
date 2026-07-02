from __future__ import annotations

from types import SimpleNamespace

import pytest

import financial_agent_runtime as runtime
from financial_agent_runtime import tool_access


def _reset() -> None:
    tool_access._ACCESS_CONFIG_CACHE.clear()


def _write_config(path, text: str):
    cfg = path / "tool-concurrency.yaml"
    cfg.write_text(text, encoding="utf-8")
    return path


def _tool(name: str):
    return SimpleNamespace(name=name)


def test_load_tool_access_config_parses_groups_and_agent_tools(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        """
groups:
  ifind:
    max_concurrency: 5
    mcp_servers: ["ifind-*"]
tool_groups:
  local_group:
    source: local
    tools: ["write_report"]
  mcp_group:
    source: mcp
    servers: ["ifind-*", "mx-ds-mcp"]
  dynamic_group:
    source: dynamic
agent_tools:
  analyst:
    tool_groups: ["local_group", "mcp_group", "dynamic_group"]
    tools: ["direct_tool"]
""",
    )

    cfg = runtime.load_tool_access_config(tmp_path)

    assert cfg.tool_groups["local_group"].source == "local"
    assert cfg.tool_groups["local_group"].tools == ("write_report",)
    assert cfg.tool_groups["mcp_group"].servers == ("ifind-*", "mx-ds-mcp")
    assert cfg.agent_tools["analyst"].tool_groups == (
        "local_group",
        "mcp_group",
        "dynamic_group",
    )
    assert cfg.agent_tools["analyst"].tools == ("direct_tool",)


def test_resolve_agent_tools_supports_local_mcp_dynamic_and_direct(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        """
tool_groups:
  local_group:
    source: local
    tools: ["write_report"]
  mcp_group:
    source: mcp
    servers: ["ifind-*"]
  dynamic_group:
    source: dynamic
agent_tools:
  analyst:
    tool_groups: ["local_group", "mcp_group", "dynamic_group"]
    tools: ["direct_tool"]
""",
    )
    cfg = runtime.load_tool_access_config(tmp_path)
    write_report = _tool("write_report")
    direct_tool = _tool("direct_tool")
    mcp_tool = _tool("ifind_quote")
    search_tool = _tool("web_search")

    tools = runtime.resolve_agent_tools(
        "analyst",
        access_config=cfg,
        local_tools=runtime.build_tool_catalog([write_report, direct_tool]),
        mcp_tool_groups={"mcp_group": [mcp_tool]},
        dynamic_tool_groups={"dynamic_group": [search_tool]},
    )

    assert tools == [write_report, mcp_tool, search_tool, direct_tool]


def test_mcp_server_names_for_tool_group_supports_patterns(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        """
tool_groups:
  data:
    source: mcp
    servers: ["ifind-*", "mx-ds-mcp"]
agent_tools:
  analyst:
    tool_groups: ["data"]
""",
    )
    cfg = runtime.load_tool_access_config(tmp_path)

    assert runtime.mcp_tool_group_names_for_agent(cfg, "analyst") == ("data",)
    assert runtime.mcp_server_names_for_tool_group(
        cfg,
        "data",
        ["ifind-stock", "ifind-news", "mx-ds-mcp", "other"],
    ) == {"ifind-stock", "ifind-news", "mx-ds-mcp"}


def test_resolve_agent_tools_errors_on_unknown_agent_or_tool(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        """
tool_groups:
  local_group:
    source: local
    tools: ["missing_tool"]
agent_tools:
  analyst:
    tool_groups: ["local_group"]
""",
    )
    cfg = runtime.load_tool_access_config(tmp_path)

    with pytest.raises(KeyError, match="No root tool access config"):
        runtime.resolve_agent_tools(
            "unknown",
            access_config=cfg,
            local_tools={},
        )

    with pytest.raises(KeyError, match="Unknown tool 'missing_tool'"):
        runtime.resolve_agent_tools(
            "analyst",
            access_config=cfg,
            local_tools={},
        )


def test_resolve_agent_tools_errors_on_missing_dynamic_or_mcp_group(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        """
tool_groups:
  mcp_group:
    source: mcp
    servers: enabled
  dynamic_group:
    source: dynamic
agent_tools:
  mcp_agent:
    tool_groups: ["mcp_group"]
  dynamic_agent:
    tool_groups: ["dynamic_group"]
""",
    )
    cfg = runtime.load_tool_access_config(tmp_path)

    with pytest.raises(KeyError, match="was not loaded"):
        runtime.resolve_agent_tools(
            "mcp_agent",
            access_config=cfg,
            local_tools={},
        )

    with pytest.raises(KeyError, match="was not provided"):
        runtime.resolve_agent_tools(
            "dynamic_agent",
            access_config=cfg,
            local_tools={},
        )
