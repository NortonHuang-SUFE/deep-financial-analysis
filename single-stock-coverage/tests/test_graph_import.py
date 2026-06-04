from __future__ import annotations

import importlib


def test_graph_imports_in_test_mode(monkeypatch):
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_TEST_MODE", "1")

    graph_module = importlib.import_module("single_stock_coverage_agent.graph")

    assert graph_module.graph == {"name": "single_stock_coverage", "test_mode": True}
