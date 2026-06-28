"""Regression tests for the Daytona artifact read/write split.

These cover the bug where artifact *reads* and existence checks ran against the
host filesystem while *writes* went to the sandbox, which (among other things)
silently reset an existing coverage_state.json on every new run.
"""

from __future__ import annotations

import shlex
from types import SimpleNamespace

import pytest

import financial_agent_runtime as runtime
from single_stock_coverage_agent import tools


class StatefulFakeSandbox:
    """Minimal in-memory stand-in for the Daytona sandbox backend."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dirs: set[str] = {"/"}

    # -- helpers -------------------------------------------------------------
    def _add_dir(self, path: str) -> None:
        parts = path.rstrip("/").split("/")
        for i in range(2, len(parts) + 1):
            self.dirs.add("/".join(parts[:i]))

    def _exists(self, path: str) -> bool:
        path = path.rstrip("/")
        return path in self.files or path in self.dirs

    # -- backend protocol ----------------------------------------------------
    def execute(self, command: str):
        tokens = shlex.split(command)
        if tokens[:2] == ["test", "-e"]:
            return SimpleNamespace(exit_code=0 if self._exists(tokens[2]) else 1, output="")
        if tokens[:2] == ["mkdir", "-p"]:
            for path in tokens[2:]:
                self._add_dir(path)
            return SimpleNamespace(exit_code=0, output="")
        if tokens[0] == "find":
            base = tokens[1].rstrip("/")
            children = {
                p
                for p in (self.files.keys() | self.dirs)
                if p.startswith(base + "/") and "/" not in p[len(base) + 1 :]
            }
            return SimpleNamespace(exit_code=0, output="\n".join(sorted(children)))
        if tokens[0] == "cp":
            self.files[tokens[2]] = self.files[tokens[1]]
            return SimpleNamespace(exit_code=0, output="")
        return SimpleNamespace(exit_code=0, output="")

    def upload_files(self, files):
        for path, data in files:
            self._add_dir(path.rsplit("/", 1)[0])
            self.files[path] = data
        return None

    def download_files(self, paths):
        return [
            SimpleNamespace(
                path=p,
                content=self.files.get(p),
                error=None if p in self.files else "file_not_found",
            )
            for p in paths
        ]


@pytest.fixture
def fake_sandbox(monkeypatch):
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    monkeypatch.setenv("DAYTONA_FILE_STORAGE_ROOT", "/home/daytona/financial-analysis")
    sandbox = StatefulFakeSandbox()
    monkeypatch.setattr(runtime, "_DAYTONA_BACKEND", sandbox, raising=False)
    tools._ACTIVE_RUNS.clear()
    return sandbox


def _create_run(market: str = "A", ticker: str = "000001"):
    return tools._create_run_dir(
        company="Test Co",
        ticker=ticker,
        market=market,
        task_type="initiate",
        triggering_event="unit-test",
    )


def test_create_run_dir_writes_artifacts_into_sandbox(fake_sandbox):
    run_dir = _create_run()

    manifest = str(run_dir / "run_manifest.json")
    coverage_state = str(run_dir.parent.parent / "coverage_state.json")
    assert manifest in fake_sandbox.files
    assert coverage_state in fake_sandbox.files
    # Nothing should have been written to the host repo path.
    assert not (run_dir / "run_manifest.json").exists()


def test_second_run_preserves_existing_coverage_state(fake_sandbox, monkeypatch):
    timestamps = iter(["20260625-090000", "20260625-091500"])
    monkeypatch.setattr(tools, "_timestamp", lambda: next(timestamps))

    first_run = _create_run()
    coverage_state = str(first_run.parent.parent / "coverage_state.json")

    # Simulate accumulated coverage state from the first run.
    fake_sandbox.files[coverage_state] = b'{"coverage_status": "active", "kept": true}'
    tools._ACTIVE_RUNS.clear()

    second_run = _create_run()

    assert second_run != first_run
    # The existing coverage_state must NOT be clobbered by the second run.
    assert fake_sandbox.files[coverage_state] == b'{"coverage_status": "active", "kept": true}'
