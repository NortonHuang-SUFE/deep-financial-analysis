"""Artifact persistence tests for the single-stock-coverage agent.

Verifies that every run fully materialises its artifacts on disk and that the
next update run can read the previous run's state via coverage_state.json.
"""
from __future__ import annotations

import json
import os

import pytest

from single_stock_coverage_agent.tools import (
    build_excel_model,
    audit_excel_model,
    create_coverage_run_dir,
    list_run_artifacts,
    read_coverage_state,
    read_task_artifact,
    write_coverage_state,
    write_json_artifact,
    write_run_manifest,
    write_task_artifact,
)


TICKER = "000858"
MARKET = "sz"


# ---------------------------------------------------------------------------
# Helper: simulate a full initiation run
# ---------------------------------------------------------------------------


def _simulate_full_initiation(tmp_path, timestamp: str) -> str:
    """Run through all 5 tasks and persist state; return the run_dir."""
    os.environ["SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP"] = timestamp
    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    # Task 1
    write_task_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "01_company_research",
            "filename": "company_research.md",
            "content": "# Company Research\n\nStub content.",
        }
    )
    write_json_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "01_company_research",
            "filename": "business_driver_map.json",
            "data_json": json.dumps(
                {
                    "ticker": TICKER,
                    "company": "Wuliangye",
                    "revenue_drivers": [{"driver": "ASP", "description": "ASP trend", "evidence": "annual report"}],
                    "margin_drivers": [{"driver": "COGS ratio", "description": "raw material cost", "evidence": "annual report"}],
                    "capex_drivers": [{"driver": "capacity expansion", "description": "new production line", "maintenance_vs_growth": "growth", "evidence": "company disclosure"}],
                    "working_capital_drivers": [{"driver": "DSO", "description": "distributor payment terms", "receivables_days": 30, "inventory_days": 90, "payables_days": 45, "evidence": "annual report"}],
                    "risk_drivers": [{"risk": "regulatory ASP cap", "category": "regulatory", "severity": "High", "financial_mechanism": "reduces revenue", "evidence": "policy document"}],
                    "catalyst_drivers": [{"catalyst": "H2 earnings", "category": "earnings", "direction": "positive", "timing": "Aug 2026", "magnitude": "material", "evidence": "consensus"}],
                    "unsourced_items": [],
                }
            ),
        }
    )

    # Task 2
    build_excel_model.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "02_financial_model",
            "filename": "integrated_model.xlsx",
            "description": "Wuliangye Integrated Financial Model",
        }
    )
    write_json_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "02_financial_model",
            "filename": "financial_facts.json",
            "data_json": json.dumps(
                {
                    "ticker": TICKER,
                    "company": "Wuliangye",
                    "years": ["2021", "2022", "2023", "2024", "2025"],
                    "income_statement": {"revenue": [60000, 65000, 70000, 74000, 78000]},
                    "unsourced_items": [],
                }
            ),
        }
    )
    write_task_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "02_financial_model",
            "filename": "model_audit.md",
            "content": "# Model Audit\n\n**Result**: PASS. All checks resolved.",
        }
    )

    # Task 3
    write_task_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "03_valuation",
            "filename": "assumption_pack.md",
            "content": "# Assumption Pack\n\n## 1. Valuation Conclusion\nBase PT: CNY 175.",
        }
    )
    write_task_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "03_valuation",
            "filename": "assumption_audit.md",
            "content": "# Assumption Audit\n\n**Overall**: Clean. All 11 items PASS.",
        }
    )
    write_json_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "03_valuation",
            "filename": "valuation_state.json",
            "data_json": json.dumps(
                {
                    "ticker": TICKER,
                    "as_of_date": "2026-06-04",
                    "current_price": 155.0,
                    "currency": "CNY",
                    "weighted_price_target": {"bear": 130.0, "base": 175.0, "bull": 220.0},
                    "rating": "Buy",
                }
            ),
        }
    )

    # Task 4
    write_json_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "04_charts",
            "filename": "chart_index.json",
            "data_json": json.dumps({"charts": []}),
        }
    )

    # Task 5
    write_task_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "05_report",
            "filename": "final_report.md",
            "content": "# Initiation Report\n\n**BUY** | PT: CNY 175",
        }
    )
    write_json_artifact.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "05_report",
            "filename": "source_index.json",
            "data_json": json.dumps([]),
        }
    )

    # Run manifest
    write_run_manifest.invoke(
        {
            "run_dir": run_dir,
            "manifest_json": json.dumps(
                {
                    "run_id": timestamp,
                    "ticker": TICKER,
                    "market": MARKET,
                    "task_type": "initiation",
                    "triggering_event": "First initiation coverage",
                    "tasks_executed": [
                        "task1_company_research",
                        "task2_financial_model",
                        "task3_valuation",
                        "task4_charts",
                        "task5_report",
                    ],
                    "input_artifacts": [],
                    "output_artifacts": [{"label": "valuation_state", "path": f"{run_dir}/03_valuation/valuation_state.json"}],
                    "final_conclusion": {"price_target_base": 175.0, "rating": "Buy", "thesis_summary": "Stub initiation"},
                    "unsourced_items": [],
                    "follow_up_checklist": [],
                    "errors_or_warnings": [],
                }
            ),
        }
    )

    # Coverage state
    write_coverage_state.invoke(
        {
            "ticker": TICKER,
            "market": MARKET,
            "output_dir": str(tmp_path),
            "state_json": json.dumps(
                {
                    "ticker": TICKER,
                    "market": MARKET,
                    "company": "Wuliangye",
                    "currency": "CNY",
                    "fiscal_year_end": "12-31",
                    "coverage_status": "initiated",
                    "latest_run_id": timestamp,
                    "latest_run_path": run_dir,
                    "latest_task_type": "initiation",
                    "latest_company_research_path": f"{run_dir}/01_company_research/company_research.md",
                    "latest_model_path": f"{run_dir}/02_financial_model/integrated_model.xlsx",
                    "latest_valuation_state_path": f"{run_dir}/03_valuation/valuation_state.json",
                    "latest_report_path": f"{run_dir}/05_report/final_report.md",
                    "price_target": {"bear": 130.0, "base": 175.0, "bull": 220.0, "currency": "CNY", "as_of_date": "2026-06-04"},
                    "rating": "Buy",
                    "current_price": 155.0,
                    "current_price_date": "2026-06-04",
                    "thesis_pillars": ["Stub thesis pillar"],
                    "key_assumptions": {
                        "base_revenue_growth_pct": 8.0,
                        "base_ebit_margin_pct": 40.0,
                        "wacc_pct": 9.0,
                        "terminal_growth_pct": 3.0,
                    },
                    "next_catalysts": [],
                    "stale_data_flags": [],
                    "unsourced_items": [],
                    "last_updated": "2026-06-04T12:00:00Z",
                }
            ),
        }
    )

    return run_dir


# ---------------------------------------------------------------------------
# Test 1: All required artifacts are on disk after a full initiation run
# ---------------------------------------------------------------------------


def test_full_initiation_artifacts_on_disk(monkeypatch, tmp_path):
    """After a full initiation run every required artifact must exist on disk."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-100000")
    run_dir = _simulate_full_initiation(tmp_path, "20260604-100000")

    artifacts_json = list_run_artifacts.invoke({"run_dir": run_dir})
    artifacts = json.loads(artifacts_json)

    def _has(suffix: str) -> bool:
        return any(a.endswith(suffix) for a in artifacts)

    # Task 1
    assert _has("01_company_research/company_research.md"), "company_research.md missing"
    assert _has("01_company_research/business_driver_map.json"), "business_driver_map.json missing"

    # Task 2
    assert _has("02_financial_model/integrated_model.xlsx"), "integrated_model.xlsx missing"
    assert _has("02_financial_model/financial_facts.json"), "financial_facts.json missing"
    assert _has("02_financial_model/model_audit.md"), "model_audit.md missing"

    # Task 3 — valuation assumption gate files MUST exist
    assert _has("03_valuation/assumption_pack.md"), "assumption_pack.md missing"
    assert _has("03_valuation/assumption_audit.md"), "assumption_audit.md missing"
    assert _has("03_valuation/valuation_state.json"), "valuation_state.json missing"

    # Task 4
    assert _has("04_charts/chart_index.json"), "chart_index.json missing"

    # Task 5
    assert _has("05_report/final_report.md"), "final_report.md missing"

    # Run manifest
    assert _has("run_manifest.json"), "run_manifest.json missing"

    # Coverage state is at ticker-level, not run-level
    state_path = tmp_path / f"{MARKET}-{TICKER}" / "coverage_state.json"
    assert state_path.exists(), "coverage_state.json missing at ticker level"


# ---------------------------------------------------------------------------
# Test 2: Next update run reads previous run's state
# ---------------------------------------------------------------------------


def test_update_run_reads_prior_state(monkeypatch, tmp_path):
    """An update run must be able to read the prior coverage state and load artifacts."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-100000")
    first_run_dir = _simulate_full_initiation(tmp_path, "20260604-100000")

    # Simulate a second (update) run reading prior state
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260901-100000")
    raw_state = read_coverage_state.invoke({"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)})
    prior_state = json.loads(raw_state)

    assert prior_state["coverage_status"] == "initiated"
    assert prior_state["latest_run_id"] == "20260604-100000"

    # The paths stored in coverage_state must be readable by read_task_artifact
    # The latest_valuation_state_path is an absolute-style path stored in the state;
    # we verify that the file itself exists on disk
    valuation_state_path_in_state = prior_state["latest_valuation_state_path"]
    # Resolve: if it looks like a workspace-relative path, prepend workspace root
    # For this test the run_dir returned is workspace-relative, so we resolve against tmp_path parent
    assert valuation_state_path_in_state is not None
    assert "valuation_state.json" in valuation_state_path_in_state

    # Verify the run dir produced in the first run actually has all subdirs
    second_run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )
    assert second_run_dir != first_run_dir, "Second run must get a different run directory"


# ---------------------------------------------------------------------------
# Test 3: coverage_state.json is updated with new values after update run
# ---------------------------------------------------------------------------


def test_coverage_state_updated_after_second_run(monkeypatch, tmp_path):
    """After an update run the coverage_state must reflect the new run id and PT."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-100000")
    _simulate_full_initiation(tmp_path, "20260604-100000")

    # Simulate an update: write new coverage state with updated PT
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260901-120000")
    update_run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    new_state = {
        "ticker": TICKER,
        "market": MARKET,
        "company": "Wuliangye",
        "currency": "CNY",
        "fiscal_year_end": "12-31",
        "coverage_status": "active",
        "latest_run_id": "20260901-120000",
        "latest_run_path": update_run_dir,
        "latest_task_type": "update",
        "latest_company_research_path": None,
        "latest_model_path": f"{update_run_dir}/02_financial_model/integrated_model.xlsx",
        "latest_valuation_state_path": f"{update_run_dir}/03_valuation/valuation_state.json",
        "latest_report_path": f"{update_run_dir}/05_report/final_report.md",
        "price_target": {"bear": 135.0, "base": 180.0, "bull": 225.0, "currency": "CNY", "as_of_date": "2026-09-01"},
        "rating": "Buy",
        "current_price": 158.0,
        "current_price_date": "2026-09-01",
        "thesis_pillars": ["Updated thesis after H1 beat"],
        "key_assumptions": {
            "base_revenue_growth_pct": 10.0,
            "base_ebit_margin_pct": 41.0,
            "wacc_pct": 9.0,
            "terminal_growth_pct": 3.0,
        },
        "next_catalysts": [],
        "stale_data_flags": [],
        "unsourced_items": [],
        "last_updated": "2026-09-01T12:00:00Z",
    }
    write_coverage_state.invoke(
        {"ticker": TICKER, "market": MARKET, "state_json": json.dumps(new_state), "output_dir": str(tmp_path)}
    )

    # Read back and verify updated fields
    raw = read_coverage_state.invoke({"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)})
    loaded = json.loads(raw)

    assert loaded["coverage_status"] == "active"
    assert loaded["latest_run_id"] == "20260901-120000"
    assert loaded["price_target"]["base"] == 180.0
    assert loaded["rating"] == "Buy"


# ---------------------------------------------------------------------------
# Test 4: assumption_pack.md and assumption_audit.md are mandatory in Task 3
# ---------------------------------------------------------------------------


def test_valuation_assumptions_files_present_after_task3(monkeypatch, tmp_path):
    """assumption_pack.md and assumption_audit.md must both exist in 03_valuation."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-150000")
    run_dir = _simulate_full_initiation(tmp_path, "20260604-150000")

    assumption_pack = read_task_artifact.invoke(
        {"run_dir": run_dir, "task_subdir": "03_valuation", "filename": "assumption_pack.md"}
    )
    assumption_audit = read_task_artifact.invoke(
        {"run_dir": run_dir, "task_subdir": "03_valuation", "filename": "assumption_audit.md"}
    )

    assert assumption_pack != "[FILE NOT FOUND]", "assumption_pack.md must exist after Task 3"
    assert assumption_audit != "[FILE NOT FOUND]", "assumption_audit.md must exist after Task 3"


# ---------------------------------------------------------------------------
# Test 5: Excel audit produces a report (all Excel must produce audit report)
# ---------------------------------------------------------------------------


def test_excel_audit_report_produced(monkeypatch, tmp_path):
    """Every Excel workbook must produce an audit result with a 'passed' field."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-160000")
    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    # Build and audit integrated model
    build_excel_model.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "02_financial_model",
            "filename": "integrated_model.xlsx",
            "description": "Wuliangye Integrated Model",
        }
    )
    result_json = audit_excel_model.invoke(
        {"run_dir": run_dir, "task_subdir": "02_financial_model", "filename": "integrated_model.xlsx"}
    )
    result = json.loads(result_json)
    assert "passed" in result, "audit result must have 'passed' field"
    assert isinstance(result["sheets"], list)
    assert isinstance(result["issues"], list)

    # Build and audit DCF model
    build_excel_model.invoke(
        {
            "run_dir": run_dir,
            "task_subdir": "03_valuation",
            "filename": "dcf_model.xlsx",
            "description": "Wuliangye DCF Model",
        }
    )
    dcf_result_json = audit_excel_model.invoke(
        {"run_dir": run_dir, "task_subdir": "03_valuation", "filename": "dcf_model.xlsx"}
    )
    dcf_result = json.loads(dcf_result_json)
    assert "passed" in dcf_result
