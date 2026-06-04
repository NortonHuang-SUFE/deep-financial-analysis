from __future__ import annotations

import json

from single_stock_coverage_agent.config import load_config
from single_stock_coverage_agent.tools import (
    build_excel_model,
    audit_excel_model,
    create_coverage_run_dir,
    read_coverage_state,
    write_coverage_state,
    write_json_artifact,
    write_run_manifest,
    write_task_artifact,
)


def test_config_loads():
    cfg = load_config()

    assert cfg.model.default is not None
    assert cfg.model.default != ""


def test_output_dir_default():
    cfg = load_config()

    assert cfg.output.dir == "./coverage"


def test_create_coverage_run_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-120000")

    rel_run_dir = create_coverage_run_dir.invoke(
        {"ticker": "000858", "market": "sz", "output_dir": str(tmp_path)}
    )

    run_dir = tmp_path / "sz-000858" / "runs" / "20260604-120000"
    assert run_dir.is_dir(), f"Expected run dir to exist: {run_dir}"

    for subdir in ("01_company_research", "02_financial_model", "03_valuation", "04_charts", "05_report"):
        assert (run_dir / subdir).is_dir(), f"Expected subdir to exist: {subdir}"


def test_write_and_read_coverage_state(tmp_path):
    state = {"ticker": "000858", "market": "sz", "rating": "BUY", "price_target": 380.0}
    state_json = json.dumps(state)

    write_coverage_state.invoke(
        {"ticker": "000858", "market": "sz", "state_json": state_json, "output_dir": str(tmp_path)}
    )

    raw = read_coverage_state.invoke(
        {"ticker": "000858", "market": "sz", "output_dir": str(tmp_path)}
    )
    loaded = json.loads(raw)

    assert loaded["ticker"] == "000858"
    assert loaded["rating"] == "BUY"
    assert loaded["price_target"] == 380.0


def test_write_task_artifact(monkeypatch, tmp_path):
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-130000")

    run_dir = str(tmp_path / "sz-000858" / "runs" / "20260604-130000")
    content = "# Company Research\n\nTest content."

    write_task_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "01_company_research",
            "filename": "company_profile.md",
            "content": content,
        }
    )

    artifact_path = tmp_path / "sz-000858" / "runs" / "20260604-130000" / "01_company_research" / "company_profile.md"
    assert artifact_path.exists(), "Expected artifact file to exist"
    assert artifact_path.read_text(encoding="utf-8") == content


def test_write_json_artifact(tmp_path):
    run_dir = str(tmp_path / "run01")
    data = {"ticker": "000858", "pe_ratio": 32.5, "pb_ratio": 8.1}
    data_json = json.dumps(data)

    write_json_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "01_company_research",
            "filename": "financial_facts.json",
            "data_json": data_json,
        }
    )

    artifact_path = tmp_path / "run01" / "01_company_research" / "financial_facts.json"
    assert artifact_path.exists(), "Expected JSON artifact file to exist"
    loaded = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert loaded["ticker"] == "000858"
    assert loaded["pe_ratio"] == 32.5


def test_audit_excel_model(tmp_path):
    run_dir = str(tmp_path / "run_excel")

    build_excel_model.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "02_financial_model",
            "filename": "model_000858.xlsx",
            "description": "Wuliangye (000858.SZ) Financial Model",
        }
    )

    result_json = audit_excel_model.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "02_financial_model",
            "filename": "model_000858.xlsx",
        }
    )

    result = json.loads(result_json)
    assert isinstance(result["sheets"], list)
    assert "Checks" in result["sheets"] or any(
        s.lower() in ("checks", "check") for s in result["sheets"]
    )


def test_run_manifest(tmp_path):
    run_dir = str(tmp_path / "run_manifest_test")
    manifest = {
        "run_id": "20260604-120000",
        "ticker": "000858",
        "market": "sz",
        "task_type": "initiation",
        "conclusion": "BUY with PT 380",
    }
    manifest_json = json.dumps(manifest)

    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": manifest_json})

    manifest_path = tmp_path / "run_manifest_test" / "run_manifest.json"
    assert manifest_path.exists(), "Expected run_manifest.json to exist"
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["ticker"] == "000858"
    assert loaded["task_type"] == "initiation"
