from __future__ import annotations

from pathlib import Path

from morning_note_agent import tools


def _guard_remote_host_writes(monkeypatch):
    original_mkdir = Path.mkdir
    original_write_text = Path.write_text

    def guarded_mkdir(self, *args, **kwargs):
        if str(self).startswith("/home/daytona/"):
            raise AssertionError(f"unexpected host mkdir for Daytona path: {self}")
        return original_mkdir(self, *args, **kwargs)

    def guarded_write_text(self, *args, **kwargs):
        if str(self).startswith("/home/daytona/"):
            raise AssertionError(f"unexpected host write_text for Daytona path: {self}")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)
    monkeypatch.setattr(Path, "write_text", guarded_write_text)


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


def test_timestamp_detection_ignores_grandparent_timestamp(monkeypatch, tmp_path):
    tools._TASK_OUTPUT_DIRS.clear()
    monkeypatch.setenv("AGENT_FILE_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_TIMESTAMP", "20260625-111111")
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_SCOPE", "run-nested")

    output_dir = tmp_path / "out" / "20260625-101500" / "morning-note" / "nested"
    out_path = tools.create_task_output_dir.invoke({"output_dir": str(output_dir)})

    assert out_path == str((output_dir / "20260625-111111").resolve())


def test_daytona_markdown_write_uses_backend_artifact_helpers(monkeypatch):
    tools._TASK_OUTPUT_DIRS.clear()
    _guard_remote_host_writes(monkeypatch)
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    monkeypatch.setenv("DAYTONA_FILE_STORAGE_ROOT", "/home/daytona/financial-analysis")
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_TIMESTAMP", "20260625-120000")
    monkeypatch.setenv("MORNING_NOTE_OUTPUT_SCOPE", "daytona-text")
    monkeypatch.setattr(tools, "backend_is_daytona", lambda: True)

    ensured: list[str] = []
    writes: list[tuple[str, str, str]] = []
    monkeypatch.setattr(tools, "ensure_artifact_dir", lambda path: ensured.append(str(path)))
    monkeypatch.setattr(
        tools,
        "write_text_artifact",
        lambda path, text, encoding="utf-8": writes.append((str(path), text, encoding)),
    )

    result = tools.write_markdown_report.invoke({"markdown": "# Note\n"})

    expected_dir = "/home/daytona/financial-analysis/out/20260625-120000"
    expected_path = f"{expected_dir}/morning-note.md"
    assert result == expected_path
    assert ensured == [expected_dir]
    assert writes == [(expected_path, "# Note\n", "utf-8")]
