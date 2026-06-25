from __future__ import annotations

from pathlib import Path

from morning_note_agent import tools


def test_output_dir_cache_is_scoped_and_expires(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_TIMESTAMP", "20260616-090000")
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_SCOPE", "run-a")

    first = tools._timestamped_output_dir()
    same = tools._timestamped_output_dir()

    monkeypatch.setenv("MORNING_NOTE_OUTPUT_SCOPE", "run-b")
    other_scope = tools._timestamped_output_dir()

    monkeypatch.setenv("MORNING_NOTE_OUTPUT_SCOPE", "run-c")
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.delenv("MORNING_NOTE_OUTPUT_TIMESTAMP")
    monkeypatch.setattr(tools, "_CACHE_TTL_SECONDS", 0)
    expired_first = tools._timestamped_output_dir()
    expired_second = tools._timestamped_output_dir()

    assert first == tmp_path / "out" / "20260616-090000"
    assert same == first
    assert other_scope == first
    assert expired_first != expired_second


def test_artifact_tools_default_to_configured_storage_root_and_return_absolute_paths(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_TIMESTAMP", "20260616-091500")
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_SCOPE", "run-abs")

    out_path = tools.create_task_output_dir.invoke({})
    md_path = tools.write_markdown_report.invoke({"markdown": "# Note\n"})
    json_path = tools.write_json_artifact.invoke({"data_json": "{\"ok\": true}"})

    assert out_path == str((tmp_path / "out" / "20260616-091500").resolve())
    assert md_path == str((tmp_path / "out" / "20260616-091500" / "morning-note.md").resolve())
    assert json_path == str((tmp_path / "out" / "20260616-091500" / "morning-note-sources.json").resolve())
    assert Path(md_path).read_text(encoding="utf-8") == "# Note\n"


def test_orchestrator_output_dir_is_used_exactly(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    monkeypatch.delenv("MORNING_NOTE_OUTPUT_TIMESTAMP", raising=False)

    output_dir = tmp_path / "out" / "20260625-101500" / "morning-note"
    out_path = tools.create_task_output_dir.invoke({"output_dir": str(output_dir)})
    md_path = tools.write_markdown_report.invoke(
        {"markdown": "# Note\n", "output_dir": str(output_dir)}
    )
    json_path = tools.write_json_artifact.invoke(
        {"data_json": "{\"ok\": true}", "output_dir": str(output_dir)}
    )

    assert out_path == str(output_dir.resolve())
    assert md_path == str((output_dir / "morning-note.md").resolve())
    assert json_path == str((output_dir / "morning-note-sources.json").resolve())
    assert not any(path.is_dir() for path in output_dir.glob("20??????-??????*"))
