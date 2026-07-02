from __future__ import annotations

import yaml

import financial_agent_runtime as runtime


def _clear_env(monkeypatch):
    for env_name in [
        "IFIND_MCP_AUTHORIZATION",
        "IFIND_MCP_TOKEN",
        "MX_DS_MCP_API_KEY",
        "MX_DS_MCP_EM_API_KEY",
        "EASTMONEY_MX_DS_MCP_API_KEY",
        "MX_DS_MCP_URL",
        "MX_DS_MCP_TRANSPORT",
        "MX_DS_MCP_MCP_URL",
        "MX_DS_MCP_MCP_TRANSPORT",
    ]:
        monkeypatch.delenv(env_name, raising=False)


def test_nested_mcp_servers_env_header_timeout_and_allowlist(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("IFIND_MCP_TOKEN", "ifind-token")
    monkeypatch.setenv("MX_DS_MCP_API_KEY", "mx-key")

    data = yaml.safe_load(
        """
mcp:
  servers:
    ifind-stock:
      url: https://ifind.example/mcp/
      transport: streamable_http
    mx-ds-mcp:
      url: https://mxapi.eastmoney.com/mxds/mcp
      transport: streamable-http
      connectTimeout: 10
      timeout: 120
      headers:
        em_api_key: "${MX_DS_MCP_API_KEY}"
"""
    )
    mcp = {
        name: runtime.MCPServerConfig(**value)
        for name, value in runtime.mcp_servers_from_yaml_data(data).items()
    }

    runtime.apply_mcp_env_overrides(mcp)

    assert mcp["mx-ds-mcp"].transport == "streamable_http"
    assert mcp["mx-ds-mcp"].connect_timeout == 10
    configs = runtime.enabled_mcp_server_configs(
        mcp,
        server_names={"mx-ds-mcp"},
    )
    assert configs == {
        "mx-ds-mcp": {
            "url": "https://mxapi.eastmoney.com/mxds/mcp",
            "transport": "streamable_http",
            "headers": {"em_api_key": "mx-key"},
            "timeout": 120,
        }
    }

    all_configs = runtime.enabled_mcp_server_configs(mcp)
    assert all_configs["ifind-stock"]["headers"] == {
        "Authorization": "Bearer ifind-token"
    }


def test_mx_ds_url_and_transport_env_aliases(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MX_DS_MCP_URL", "https://example.test/mx")
    monkeypatch.setenv("MX_DS_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MX_DS_MCP_API_KEY", "mx-key")
    mcp = {
        "mx-ds-mcp": runtime.MCPServerConfig(
            url="https://mxapi.eastmoney.com/mxds/mcp",
            transport="sse",
        )
    }

    runtime.apply_mcp_env_overrides(mcp)
    configs = runtime.enabled_mcp_server_configs(mcp)

    assert configs["mx-ds-mcp"]["url"] == "https://example.test/mx"
    assert configs["mx-ds-mcp"]["transport"] == "streamable_http"
    assert configs["mx-ds-mcp"]["headers"] == {"em_api_key": "mx-key"}


def test_connect_timeout_is_adapter_timeout_fallback(monkeypatch):
    _clear_env(monkeypatch)
    mcp = {
        "mx-ds-mcp": runtime.MCPServerConfig(
            url="https://mxapi.eastmoney.com/mxds/mcp",
            transport="streamable-http",
            connectTimeout=10,
            headers={"em_api_key": "${MX_DS_MCP_API_KEY}"},
        )
    }
    monkeypatch.setenv("MX_DS_MCP_API_KEY", "mx-key")

    runtime.apply_mcp_env_overrides(mcp)
    configs = runtime.enabled_mcp_server_configs(mcp)

    assert configs["mx-ds-mcp"] == {
        "url": "https://mxapi.eastmoney.com/mxds/mcp",
        "transport": "streamable_http",
        "headers": {"em_api_key": "mx-key"},
        "timeout": 10,
    }


def test_mcp_tool_group_server_names_supports_patterns():
    groups = {
        "default": runtime.MCPToolGroupConfig(servers=["ifind-*", "mx-ds-mcp"]),
        "mx": runtime.MCPToolGroupConfig(servers=["mx-ds-mcp"]),
    }
    all_servers = ["ifind-stock", "ifind-news", "mx-ds-mcp", "other"]

    assert runtime.mcp_tool_group_server_names(
        groups,
        "default",
        all_servers,
    ) == {"ifind-stock", "ifind-news", "mx-ds-mcp"}
    assert runtime.mcp_tool_group_server_names(groups, "mx", all_servers) == {
        "mx-ds-mcp"
    }
    assert runtime.mcp_tool_group_server_names(
        {},
        "missing",
        all_servers,
    ) == set(all_servers)
