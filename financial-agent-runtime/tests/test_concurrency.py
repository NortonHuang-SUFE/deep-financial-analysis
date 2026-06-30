from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import financial_agent_runtime as runtime
from financial_agent_runtime import concurrency as conc


def _reset() -> None:
    """Clear the process-global caches so each test starts clean."""
    conc._CONFIG_CACHE.clear()
    conc._REGISTRY.clear()
    conc._SEMAPHORES.clear()


def _write_config(path, text: str):
    cfg = path / "tool-concurrency.yaml"
    cfg.write_text(text, encoding="utf-8")
    return path


def _tool(name: str):
    return SimpleNamespace(name=name)


def _request(name: str, call_id: str = "0"):
    return SimpleNamespace(tool_call={"name": name, "id": call_id})


# ── config parsing ────────────────────────────────────────────────────────────


def test_config_parsing_reads_groups(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n"
        "  ifind:\n"
        "    max_concurrency: 5\n"
        "    mcp_servers: ['ifind-*']\n",
    )
    groups = runtime.load_tool_concurrency_config(tmp_path)
    assert groups["ifind"]["limit"] == 5
    assert groups["ifind"]["mcp_server_globs"] == ["ifind-*"]
    assert groups["ifind"]["tool_globs"] == []


def test_missing_config_returns_empty(tmp_path):
    _reset()
    assert runtime.load_tool_concurrency_config(tmp_path) == {}


def test_invalid_max_concurrency_skipped(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n"
        "  bad:\n"
        "    max_concurrency: 0\n"
        "    tools: ['x']\n"
        "  good:\n"
        "    max_concurrency: 3\n"
        "    tools: ['y']\n",
    )
    groups = runtime.load_tool_concurrency_config(tmp_path)
    assert "bad" not in groups
    assert groups["good"]["limit"] == 3


def test_env_var_overrides_path(tmp_path, monkeypatch):
    _reset()
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        "groups:\n  g:\n    max_concurrency: 2\n    tools: ['t']\n", encoding="utf-8"
    )
    monkeypatch.setenv("TOOL_CONCURRENCY_CONFIG", str(custom))
    # workspace_root is None, but the env override still resolves the file.
    groups = runtime.load_tool_concurrency_config(None)
    assert "g" in groups


# ── matching / resolution ───────────────────────────────────────────────────


def test_register_and_resolve_by_server(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  ifind:\n    max_concurrency: 5\n    mcp_servers: ['ifind-*']\n",
    )
    runtime.register_limited_tools(
        [_tool("THS_basicData"), _tool("THS_dateQuery")],
        server_name="ifind-stock",
        workspace_root=tmp_path,
    )
    assert runtime.resolve_tool_group("THS_basicData", tmp_path) == ("ifind", 5)
    assert runtime.resolve_tool_group("THS_dateQuery", tmp_path) == ("ifind", 5)
    # A tool from an unmatched server / a local tool is never limited.
    assert runtime.resolve_tool_group("build_dcf_model", tmp_path) is None


def test_unmatched_server_registers_nothing(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  ifind:\n    max_concurrency: 5\n    mcp_servers: ['ifind-*']\n",
    )
    runtime.register_limited_tools(
        [_tool("some_tool")], server_name="other-server", workspace_root=tmp_path
    )
    assert runtime.resolve_tool_group("some_tool", tmp_path) is None


def test_resolve_by_tool_name_glob_without_registration(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  web:\n    max_concurrency: 2\n    tools: ['web_search']\n",
    )
    # No register_limited_tools call — named tools resolve straight from config.
    assert runtime.resolve_tool_group("web_search", tmp_path) == ("web", 2)
    assert runtime.resolve_tool_group("unrelated", tmp_path) is None


def test_multi_group_most_restrictive_wins(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n"
        "  a:\n    max_concurrency: 5\n    tools: ['shared_tool']\n"
        "  b:\n    max_concurrency: 2\n    tools: ['shared_*']\n",
    )
    assert runtime.resolve_tool_group("shared_tool", tmp_path) == ("b", 2)


# ── enforcement ───────────────────────────────────────────────────────────────


def _run_concurrency_probe(mw, names, *, total, sleep=0.05):
    """Fire `total` concurrent awrap_tool_call's and return the observed peak."""
    state = {"cur": 0, "max": 0}
    lock = threading.Lock()

    async def handler(request):
        with lock:
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
        await asyncio.sleep(sleep)
        with lock:
            state["cur"] -= 1
        return "ok"

    async def run():
        reqs = [_request(names[i % len(names)], str(i)) for i in range(total)]
        await asyncio.gather(*(mw.awrap_tool_call(r, handler) for r in reqs))

    asyncio.run(run())
    return state["max"]


def test_enforcement_caps_at_limit(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  g:\n    max_concurrency: 2\n    tools: ['limited_tool']\n",
    )
    mw = runtime.make_concurrency_limit_middleware(tmp_path)
    peak = _run_concurrency_probe(mw, ["limited_tool"], total=8)
    assert peak == 2


def test_enforcement_serial_when_limit_one(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  g:\n    max_concurrency: 1\n    tools: ['serial_tool']\n",
    )
    mw = runtime.make_concurrency_limit_middleware(tmp_path)
    peak = _run_concurrency_probe(mw, ["serial_tool"], total=6)
    assert peak == 1


def test_distinct_tools_share_one_budget(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  g:\n    max_concurrency: 2\n    tools: ['tool_a', 'tool_b']\n",
    )
    mw = runtime.make_concurrency_limit_middleware(tmp_path)
    # Two differently-named tools draw on the same group budget.
    peak = _run_concurrency_probe(mw, ["tool_a", "tool_b"], total=8)
    assert peak == 2


def test_unregistered_tool_is_not_throttled(tmp_path):
    _reset()
    _write_config(
        tmp_path,
        "groups:\n  g:\n    max_concurrency: 2\n    tools: ['limited_tool']\n",
    )
    mw = runtime.make_concurrency_limit_middleware(tmp_path)
    peak = _run_concurrency_probe(mw, ["free_tool"], total=6)
    assert peak >= 4  # runs unwrapped — well above the limited group's cap of 2
