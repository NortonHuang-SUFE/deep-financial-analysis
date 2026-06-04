"""Routing tests for the single-stock-coverage agent.

These tests verify that the coverage-state and run-manifest tools correctly
support the six routing scenarios defined in the coverage-state skill:

  1. 首次覆盖 (First initiation)
  2. 财报更新 (Earnings release update)
  3. 指引变化 (Guidance change)
  4. 重大公告 (Major announcement — order / capacity / price / policy)
  5. 估值刷新 (Valuation refresh — large share price move)
  6. 模型审计 (Model audit)

For each scenario the tests verify:
- The coverage state is read correctly (or absent for initiation).
- The run manifest records the correct task_type and tasks_executed.
- State is written and readable across runs (persistence contract).
"""
from __future__ import annotations

import json

import pytest

from single_stock_coverage_agent.tools import (
    create_coverage_run_dir,
    read_coverage_state,
    write_coverage_state,
    write_run_manifest,
    list_run_artifacts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TICKER = "600519"
MARKET = "sha"


def _write_initiation_state(tmp_path: object, run_id: str) -> dict:
    """Write a typical post-initiation coverage_state.json and return it."""
    state = {
        "ticker": TICKER,
        "market": MARKET,
        "company": "Kweichow Moutai",
        "currency": "CNY",
        "fiscal_year_end": "12-31",
        "coverage_status": "initiated",
        "latest_run_id": run_id,
        "latest_run_path": f"coverage/{MARKET}-{TICKER}/runs/{run_id}",
        "latest_task_type": "initiation",
        "latest_company_research_path": f"coverage/{MARKET}-{TICKER}/runs/{run_id}/01_company_research/company_research.md",
        "latest_model_path": f"coverage/{MARKET}-{TICKER}/runs/{run_id}/02_financial_model/integrated_model.xlsx",
        "latest_valuation_state_path": f"coverage/{MARKET}-{TICKER}/runs/{run_id}/03_valuation/valuation_state.json",
        "latest_report_path": f"coverage/{MARKET}-{TICKER}/runs/{run_id}/05_report/final_report.md",
        "price_target": {"bear": 1400.0, "base": 1800.0, "bull": 2200.0, "currency": "CNY", "as_of_date": "2026-06-04"},
        "rating": "Buy",
        "current_price": 1600.0,
        "current_price_date": "2026-06-04",
        "thesis_pillars": ["Premium brand pricing power", "Volume recovery post-regulatory normalisation"],
        "key_assumptions": {
            "base_revenue_growth_pct": 12.0,
            "base_ebit_margin_pct": 55.0,
            "wacc_pct": 8.5,
            "terminal_growth_pct": 3.0,
        },
        "next_catalysts": [
            {"catalyst": "H1 earnings release", "timing": "Aug 2026", "direction": "positive", "magnitude": "material"}
        ],
        "stale_data_flags": [],
        "unsourced_items": [],
        "last_updated": "2026-06-04T12:00:00Z",
    }
    write_coverage_state.invoke(
        {"ticker": TICKER, "market": MARKET, "state_json": json.dumps(state), "output_dir": str(tmp_path)}
    )
    return state


# ---------------------------------------------------------------------------
# Scenario 1: 首次覆盖 — First initiation
# ---------------------------------------------------------------------------


def test_routing_initiation_no_prior_state(monkeypatch, tmp_path):
    """First initiation: coverage_state.json must not exist before the run."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260101-090000")

    # No prior state written — read should return empty dict
    raw = read_coverage_state.invoke({"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)})
    assert raw == "{}", "Expected empty state for first initiation"

    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    manifest = {
        "run_id": "20260101-090000",
        "ticker": TICKER,
        "market": MARKET,
        "company": "Kweichow Moutai",
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
        "output_artifacts": [],
        "final_conclusion": {"price_target_base": 1800.0, "rating": "Buy", "thesis_summary": "Premium baijiu leader"},
        "unsourced_items": [],
        "follow_up_checklist": [],
        "errors_or_warnings": [],
    }
    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": json.dumps(manifest)})

    # Verify all 5 task subdirectories were created
    import os
    for subdir in ("01_company_research", "02_financial_model", "03_valuation", "04_charts", "05_report"):
        assert os.path.isdir(str(tmp_path / f"{MARKET}-{TICKER}" / "runs" / "20260101-090000" / subdir))


# ---------------------------------------------------------------------------
# Scenario 2: 财报更新 — Earnings release update
# ---------------------------------------------------------------------------


def test_routing_earnings_update(monkeypatch, tmp_path):
    """Earnings update: run only Task 2 → Task 3 → Task 5; load prior state."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260801-100000")

    prior_run_id = "20260101-090000"
    _write_initiation_state(tmp_path, prior_run_id)

    # Agent reads prior state
    raw = read_coverage_state.invoke({"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)})
    state = json.loads(raw)
    assert state["coverage_status"] == "initiated"
    assert state["latest_task_type"] == "initiation"

    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    manifest = {
        "run_id": "20260801-100000",
        "ticker": TICKER,
        "market": MARKET,
        "task_type": "update",
        "triggering_event": "H1 2026 earnings release",
        "tasks_executed": ["task2_financial_model", "task3_valuation", "task5_report"],
        "input_artifacts": [{"label": "prior_valuation_state", "path": state["latest_valuation_state_path"]}],
        "output_artifacts": [],
        "final_conclusion": {"price_target_base": 1850.0, "rating": "Buy", "thesis_summary": "Earnings beat; PT raised"},
        "unsourced_items": [],
        "follow_up_checklist": ["Confirm Q3 volume guidance in next call"],
        "errors_or_warnings": [],
    }
    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": json.dumps(manifest)})

    # Verify input_artifacts path recorded in manifest is the prior run's valuation state
    manifest_path = tmp_path / f"{MARKET}-{TICKER}" / "runs" / "20260801-100000" / "run_manifest.json"
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["task_type"] == "update"
    assert "task1_company_research" not in loaded["tasks_executed"]
    assert loaded["input_artifacts"][0]["label"] == "prior_valuation_state"


# ---------------------------------------------------------------------------
# Scenario 3: 指引变化 — Guidance change
# ---------------------------------------------------------------------------


def test_routing_guidance_change(monkeypatch, tmp_path):
    """Guidance change: run Task 2 (assumptions update) → Task 3 only."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260901-100000")

    _write_initiation_state(tmp_path, "20260101-090000")

    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    manifest = {
        "run_id": "20260901-100000",
        "ticker": TICKER,
        "market": MARKET,
        "task_type": "update",
        "triggering_event": "Management lowered FY2026 revenue guidance by 5%",
        "tasks_executed": ["task2_financial_model", "task3_valuation"],
        "input_artifacts": [],
        "output_artifacts": [],
        "final_conclusion": {"price_target_base": 1700.0, "rating": "Neutral", "thesis_summary": "Guidance cut reduces upside"},
        "unsourced_items": [],
        "follow_up_checklist": ["Monitor Q3 volume data"],
        "errors_or_warnings": [],
    }
    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": json.dumps(manifest)})

    manifest_path = tmp_path / f"{MARKET}-{TICKER}" / "runs" / "20260901-100000" / "run_manifest.json"
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "task1_company_research" not in loaded["tasks_executed"]
    assert "task2_financial_model" in loaded["tasks_executed"]
    assert "task3_valuation" in loaded["tasks_executed"]
    assert "task4_charts" not in loaded["tasks_executed"]


# ---------------------------------------------------------------------------
# Scenario 4: 重大公告 — Major announcement (order / capacity / policy)
# ---------------------------------------------------------------------------


def test_routing_major_announcement(monkeypatch, tmp_path):
    """Major announcement: run Task 1 (delta) → Task 2 (if numbers change) → Task 3."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20261001-090000")

    _write_initiation_state(tmp_path, "20260101-090000")

    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    manifest = {
        "run_id": "20261001-090000",
        "ticker": TICKER,
        "market": MARKET,
        "task_type": "update",
        "triggering_event": "Major new distribution policy announced affecting ASP",
        "tasks_executed": ["task1_company_research", "task2_financial_model", "task3_valuation"],
        "input_artifacts": [],
        "output_artifacts": [],
        "final_conclusion": {"price_target_base": 1780.0, "rating": "Buy", "thesis_summary": "Policy impact manageable; PT modestly trimmed"},
        "unsourced_items": ["Policy cap quantification not yet officially confirmed"],
        "follow_up_checklist": ["Confirm ASP impact magnitude in Q4 channel data"],
        "errors_or_warnings": [],
    }
    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": json.dumps(manifest)})

    manifest_path = tmp_path / f"{MARKET}-{TICKER}" / "runs" / "20261001-090000" / "run_manifest.json"
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "task1_company_research" in loaded["tasks_executed"]
    assert loaded["unsourced_items"] != []


# ---------------------------------------------------------------------------
# Scenario 5: 估值刷新 — Valuation refresh (large share price move)
# ---------------------------------------------------------------------------


def test_routing_valuation_refresh(monkeypatch, tmp_path):
    """Valuation refresh: share price moved >10%; only Task 3 needs to run."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20261101-110000")

    _write_initiation_state(tmp_path, "20260101-090000")

    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    manifest = {
        "run_id": "20261101-110000",
        "ticker": TICKER,
        "market": MARKET,
        "task_type": "valuation_refresh",
        "triggering_event": "Share price dropped 15% over 5 trading days — valuation refresh required",
        "tasks_executed": ["task3_valuation"],
        "input_artifacts": [
            {"label": "prior_financial_facts", "path": f"coverage/{MARKET}-{TICKER}/runs/20260101-090000/02_financial_model/financial_facts.json"},
            {"label": "prior_business_driver_map", "path": f"coverage/{MARKET}-{TICKER}/runs/20260101-090000/01_company_research/business_driver_map.json"},
        ],
        "output_artifacts": [],
        "final_conclusion": {"price_target_base": 1800.0, "rating": "Buy", "thesis_summary": "Price move increases upside; PT unchanged"},
        "unsourced_items": [],
        "follow_up_checklist": [],
        "errors_or_warnings": [],
    }
    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": json.dumps(manifest)})

    manifest_path = tmp_path / f"{MARKET}-{TICKER}" / "runs" / "20261101-110000" / "run_manifest.json"
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["task_type"] == "valuation_refresh"
    assert loaded["tasks_executed"] == ["task3_valuation"]
    assert len(loaded["input_artifacts"]) == 2


# ---------------------------------------------------------------------------
# Scenario 6: 模型审计 — Model audit
# ---------------------------------------------------------------------------


def test_routing_model_audit(monkeypatch, tmp_path):
    """Model audit: only Task 2 (audit-xls) runs; produces an audit fix checklist."""
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20261201-090000")

    _write_initiation_state(tmp_path, "20260101-090000")

    run_dir = create_coverage_run_dir.invoke(
        {"ticker": TICKER, "market": MARKET, "output_dir": str(tmp_path)}
    )

    manifest = {
        "run_id": "20261201-090000",
        "ticker": TICKER,
        "market": MARKET,
        "task_type": "model_audit",
        "triggering_event": "Scheduled model audit — 6-month post-initiation",
        "tasks_executed": ["task2_financial_model"],
        "input_artifacts": [
            {"label": "model_to_audit", "path": f"coverage/{MARKET}-{TICKER}/runs/20260101-090000/02_financial_model/integrated_model.xlsx"}
        ],
        "output_artifacts": [],
        "final_conclusion": {"price_target_base": None, "rating": "Buy", "thesis_summary": "Model audit complete; minor formula issues found"},
        "unsourced_items": [],
        "follow_up_checklist": [
            "Fix Checks sheet: cash tie-out formula missing for FY2025",
            "Update D&A schedule to reflect H1 2026 actual capex",
        ],
        "errors_or_warnings": ["Checks sheet: cash tie-out formula cell C12 is hard-coded"],
    }
    write_run_manifest.invoke({"run_dir": run_dir, "manifest_json": json.dumps(manifest)})

    manifest_path = tmp_path / f"{MARKET}-{TICKER}" / "runs" / "20261201-090000" / "run_manifest.json"
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["task_type"] == "model_audit"
    assert loaded["tasks_executed"] == ["task2_financial_model"]
    assert len(loaded["follow_up_checklist"]) > 0
    assert len(loaded["errors_or_warnings"]) > 0
