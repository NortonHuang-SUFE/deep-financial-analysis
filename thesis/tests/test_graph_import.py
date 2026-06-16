from __future__ import annotations

import importlib


def test_graph_imports_in_test_mode(monkeypatch):
    monkeypatch.setenv("THESIS_TRACKER_TEST_MODE", "1")

    graph_module = importlib.import_module("thesis_tracker_agent.graph")

    assert graph_module.graph == {
        "name": "thesis_tracker",
        "test_mode": True,
        "backend_type": "filesystem",
    }
