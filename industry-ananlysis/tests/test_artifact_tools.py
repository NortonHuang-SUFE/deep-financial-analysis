from __future__ import annotations

import json
from pathlib import Path

import pytest

import financial_agent_runtime as runtime
from market_researcher import tools


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


def test_daytona_comps_workbook_uses_temp_file_and_upload(monkeypatch):
    pytest.importorskip("openpyxl")
    tools._TASK_OUTPUT_DIRS.clear()
    _guard_remote_host_writes(monkeypatch)
    monkeypatch.setenv("AGENT_BACKEND", "daytona")
    monkeypatch.setenv("DAYTONA_FILE_STORAGE_ROOT", "/home/daytona/financial-analysis")
    monkeypatch.setenv("MARKET_RESEARCHER_OUTPUT_TIMESTAMP", "20260625-130000")
    monkeypatch.setattr(tools, "backend_is_daytona", lambda: True)

    ensured: list[str] = []
    uploads: list[tuple[str, str, int]] = []
    monkeypatch.setattr(tools, "ensure_artifact_dir", lambda path: ensured.append(str(path)))

    def fake_upload(local_path, remote_path):
        local = Path(local_path)
        assert local.exists()
        assert not str(local).startswith("/home/daytona/")
        uploads.append((str(local), str(remote_path), local.stat().st_size))

    # _save_workbook now delegates to the shared materialize_file_artifact, which
    # performs the temp-file build and upload, so patch the runtime seam it uses.
    monkeypatch.setattr(runtime, "upload_file_artifact", fake_upload)

    companies = [
        {
            "ticker": "ABC",
            "company": "ABC Co",
            "revenue_ltm": 100,
            "revenue_growth_pct": 0.1,
            "gross_profit": 50,
            "ebitda_ltm": 30,
            "net_income": 20,
            "market_cap": 200,
            "enterprise_value": 220,
            "source": "Unit test fixture",
        }
    ]

    result = tools.build_comps_excel.invoke(
        {"data_json": json.dumps(companies), "sector": "Fintech Payments"}
    )

    expected_dir = "/home/daytona/financial-analysis/out/20260625-130000"
    assert ensured == [expected_dir]
    assert result.startswith("out/20260625-130000/comps-fintech-payments-")
    assert result.endswith(".xlsx")
    assert len(uploads) == 1
    assert uploads[0][1].startswith(
        "/home/daytona/financial-analysis/out/20260625-130000/comps-fintech-payments-"
    )
    assert uploads[0][2] > 0
