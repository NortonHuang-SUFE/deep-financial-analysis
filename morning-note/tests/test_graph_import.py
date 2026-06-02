import importlib


def test_graph_imports_in_test_mode(monkeypatch):
    monkeypatch.setenv("MORNING_NOTE_TEST_MODE", "1")

    graph_module = importlib.import_module("morning_note_agent.graph")

    assert graph_module.graph == {"name": "morning_note", "test_mode": True}

