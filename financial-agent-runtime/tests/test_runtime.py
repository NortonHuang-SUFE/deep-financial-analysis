from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

import financial_agent_runtime as runtime


class FakeBackend:
    def __init__(
        self,
        *,
        execute_response=None,
        upload_response=None,
        download_responses=None,
    ):
        self.execute_response = execute_response or SimpleNamespace(exit_code=0)
        self.upload_response = upload_response
        self.download_responses = download_responses
        self.commands: list[str] = []
        self.uploads: list[list[tuple[str, bytes]]] = []
        self.downloads: list[list[str]] = []

    def execute(self, command: str):
        self.commands.append(command)
        if callable(self.execute_response):
            return self.execute_response(command)
        return self.execute_response

    def upload_files(self, files):
        self.uploads.append(list(files))
        return self.upload_response

    def download_files(self, paths):
        self.downloads.append(list(paths))
        return self.download_responses


def _use_daytona_backend(monkeypatch, backend):
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    monkeypatch.setattr(runtime, "_DAYTONA_BACKEND", backend, raising=False)
    return backend


def test_daytona_relative_root_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    monkeypatch.setenv("DAYTONA_FILE_STORAGE_ROOT", "relative/root")

    with pytest.raises(ValueError, match="absolute POSIX path"):
        runtime.file_storage_root(tmp_path)


def test_mirror_skills_upload_error_propagates(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "SKILL.md").write_text("hello", encoding="utf-8")
    backend = FakeBackend(upload_response=SimpleNamespace(error="invalid_path"))

    with pytest.raises(RuntimeError, match="invalid_path"):
        runtime.mirror_skills_into_backend(backend, skills_dir, tmp_path / "remote")


def test_mirror_skills_mkdir_failure_propagates(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "SKILL.md").write_text("hello", encoding="utf-8")
    backend = FakeBackend(execute_response=SimpleNamespace(exit_code=7, stderr="mkdir failed"))

    with pytest.raises(RuntimeError, match="mkdir failed"):
        runtime.mirror_skills_into_backend(backend, skills_dir, "/remote/root")

    assert backend.uploads == []


def test_contains_task_timestamp_dir_only_leaf_or_direct_parent():
    assert runtime.contains_task_timestamp_dir("/work/out/20260625-101500")
    assert runtime.contains_task_timestamp_dir("/work/out/20260625-101500/subdir")
    assert not runtime.contains_task_timestamp_dir(
        "/work/20260625-101500/out/subdir"
    )
    assert not runtime.contains_task_timestamp_dir("/work/out/not-a-timestamp")


def test_general_purpose_disable_registration_is_idempotent(monkeypatch):
    calls = []

    class GeneralPurposeSubagentProfile:
        def __init__(self, *, enabled=None):
            self.enabled = enabled

    class HarnessProfile:
        def __init__(self, *, general_purpose_subagent=None):
            self.general_purpose_subagent = general_purpose_subagent

    def register_harness_profile(key, profile):
        calls.append((key, profile))

    fake_deepagents = ModuleType("deepagents")
    fake_deepagents.GeneralPurposeSubagentProfile = GeneralPurposeSubagentProfile
    fake_deepagents.HarnessProfile = HarnessProfile
    fake_deepagents.register_harness_profile = register_harness_profile

    fake_models = ModuleType("deepagents._models")
    fake_models.get_model_provider = lambda model: "anthropic" if model == "claude" else None

    monkeypatch.setitem(sys.modules, "deepagents", fake_deepagents)
    monkeypatch.setitem(sys.modules, "deepagents._models", fake_models)
    runtime._GENERAL_PURPOSE_SUBAGENT_DISABLED_KEYS.clear()

    runtime.ensure_general_purpose_subagent_disabled("claude")
    runtime.ensure_general_purpose_subagent_disabled("claude")
    runtime.ensure_general_purpose_subagent_disabled(None)

    assert [key for key, _ in calls] == ["anthropic", "openai"]
    assert calls[0][1].general_purpose_subagent.enabled is False


def test_artifact_exists_uses_test_command(monkeypatch):
    backend = _use_daytona_backend(
        monkeypatch,
        FakeBackend(execute_response=lambda cmd: SimpleNamespace(exit_code=0)),
    )

    assert runtime.artifact_exists("/home/daytona/out/a.json") is True
    assert backend.commands == ["test -e /home/daytona/out/a.json"]


def test_artifact_exists_false_on_nonzero_exit(monkeypatch):
    _use_daytona_backend(
        monkeypatch,
        FakeBackend(execute_response=lambda cmd: SimpleNamespace(exit_code=1)),
    )

    assert runtime.artifact_exists("/home/daytona/out/missing.json") is False


def test_read_text_artifact_downloads_content(monkeypatch):
    backend = _use_daytona_backend(
        monkeypatch,
        FakeBackend(
            download_responses=[
                SimpleNamespace(path="/home/daytona/out/a.json", content=b"hi", error=None)
            ]
        ),
    )

    assert runtime.read_text_artifact("/home/daytona/out/a.json") == "hi"
    assert backend.downloads == [["/home/daytona/out/a.json"]]


def test_read_text_artifact_missing_ok_returns_none(monkeypatch):
    _use_daytona_backend(
        monkeypatch,
        FakeBackend(
            download_responses=[
                SimpleNamespace(path="/x", content=None, error="file_not_found")
            ]
        ),
    )

    assert runtime.read_text_artifact("/home/daytona/out/missing.json", missing_ok=True) is None


def test_read_bytes_artifact_propagates_download_error(monkeypatch):
    _use_daytona_backend(
        monkeypatch,
        FakeBackend(
            download_responses=[
                SimpleNamespace(path="/x", content=None, error="permission_denied")
            ]
        ),
    )

    with pytest.raises(RuntimeError, match="permission_denied"):
        runtime.read_bytes_artifact("/home/daytona/out/a.json")


def test_list_artifact_dir_parses_find_output(monkeypatch):
    def _execute(command):
        if command.startswith("test -e"):
            return SimpleNamespace(exit_code=0)
        return SimpleNamespace(
            exit_code=0,
            output="/home/daytona/out/runs/20260625-101500\n/home/daytona/out/runs/20260625-101600\n",
        )

    _use_daytona_backend(monkeypatch, FakeBackend(execute_response=_execute))

    entries = runtime.list_artifact_dir("/home/daytona/out/runs")
    assert [str(p) for p in entries] == [
        "/home/daytona/out/runs/20260625-101500",
        "/home/daytona/out/runs/20260625-101600",
    ]


def test_copy_artifact_uses_cp(monkeypatch):
    backend = _use_daytona_backend(
        monkeypatch, FakeBackend(execute_response=lambda cmd: SimpleNamespace(exit_code=0))
    )

    runtime.copy_artifact("/home/daytona/a.xlsx", "/home/daytona/sub/b.xlsx")

    assert backend.commands[-1] == "cp /home/daytona/a.xlsx /home/daytona/sub/b.xlsx"
    assert any(cmd.startswith("mkdir -p ") for cmd in backend.commands)


def test_materialize_file_artifact_patches_before_upload(monkeypatch):
    backend = _use_daytona_backend(monkeypatch, FakeBackend())
    order: list[str] = []

    def _producer(local_path):
        local_path.write_bytes(b"workbook-bytes")
        order.append("produced")
        return 7

    result = runtime.materialize_file_artifact("/home/daytona/out/model.xlsx", _producer)

    assert result == 7
    assert order == ["produced"]
    assert backend.uploads == [[("/home/daytona/out/model.xlsx", b"workbook-bytes")]]


def test_materialize_file_artifact_local(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_BACKEND", "local")
    dest = tmp_path / "nested" / "model.xlsx"

    def _producer(local_path):
        local_path.write_bytes(b"local-bytes")
        return "ok"

    result = runtime.materialize_file_artifact(dest, _producer)

    assert result == "ok"
    assert dest.read_bytes() == b"local-bytes"


def test_backend_error_flags_success_false(monkeypatch):
    assert runtime._backend_error(SimpleNamespace(success=False, stderr="boom")) == "boom"
    assert runtime._backend_error({"ok": False}) == "ok is False"
    assert runtime._backend_error(SimpleNamespace(exitCode=3)) == "exit code 3"
    assert runtime._backend_error(SimpleNamespace(exit_code=0)) is None
