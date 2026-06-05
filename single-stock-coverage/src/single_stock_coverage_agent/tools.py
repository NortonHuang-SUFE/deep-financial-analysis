"""Local artifact tools for the Single Stock Coverage agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


_ACTIVE_RUNS: dict[str, Path] = {}

STATEMENT_JSON_REQUIRED_FIELDS: tuple[str, ...] = (
    "statement_type",
    "canonical_row_keys",
    "line_items",
    "historical_inputs",
    "forecast_logic",
    "assumption_requirements",
    "cross_statement_dependencies",
    "source_coverage",
    "unsourced_items",
    "validation_status",
)

STATEMENT_JSON_ALLOWED_TYPES: tuple[str, ...] = (
    "income_statement",
    "balance_sheet",
    "cash_flow",
)

STATEMENT_JSON_OUTPUTS: dict[str, str] = {
    "income_statement": "income_statement_spec.json",
    "balance_sheet": "balance_sheet_spec.json",
    "cash_flow": "cash_flow_statement_spec.json",
}

STATEMENT_CANONICAL_KEYS: dict[str, tuple[str, ...]] = {
    "income_statement": (
        "revenue_total",
        "gross_profit",
        "ebit",
        "ebitda",
        "interest_expense",
        "pretax_income",
        "tax_expense",
        "net_income",
        "da_total",
    ),
    "balance_sheet": (
        "cash_and_equivalents",
        "total_current_assets",
        "total_assets",
        "total_current_liabilities",
        "total_debt",
        "retained_earnings",
        "total_equity",
        "total_liabilities_and_equity",
    ),
    "cash_flow": (
        "net_income_cf",
        "da_addback",
        "nwc_change",
        "cfo_total",
        "capex",
        "cfi_total",
        "debt_proceeds_repayments",
        "dividends",
        "cff_total",
        "beginning_cash",
        "ending_cash",
    ),
}

STATEMENT_DEPENDENCY_HINTS: dict[str, tuple[str, ...]] = {
    "income_statement": (
        "revenue_build.total_revenue",
        "debt_interest.interest_expense",
        "share_count.diluted_shares",
    ),
    "balance_sheet": (
        "cash_flow.ending_cash",
        "income_statement.net_income",
        "share_count.dividends",
    ),
    "cash_flow": (
        "income_statement.net_income",
        "ppe_da.da_total",
        "balance_sheet.cash_and_equivalents",
    ),
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    return _project_root().parent


def _resolve_workspace_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else _workspace_root() / candidate


def _slugify(text: str, fallback: str = "unknown") -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text).strip()).strip("-")
    return normalized.lower() or fallback


def _safe_market(market: str) -> str:
    return _slugify(market or "market", "market")


def _safe_ticker(ticker: str) -> str:
    return _slugify(ticker or "ticker", "ticker")


def _coverage_root(output_dir: str = "./coverage") -> Path:
    return _resolve_workspace_path(output_dir)


def _coverage_dir(market: str, ticker: str, output_dir: str = "./coverage") -> Path:
    return _coverage_root(output_dir) / f"{_safe_market(market)}-{_safe_ticker(ticker)}"


def _relative_to_workspace(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_workspace_root()))
    except ValueError:
        return str(path.resolve())


def _json_loads(data_json: str, field_name: str) -> Any:
    try:
        return json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc}") from exc


def _read_json_file(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _statement_model_dir(run_dir: Path) -> Path:
    return run_dir / "02_financial_model"


def _task1_dir(run_dir: Path) -> Path:
    return run_dir / "01_company_research"


def _json_result(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _statement_context_payload(statement_type: str, run_dir: Path) -> dict[str, Any]:
    if statement_type not in STATEMENT_JSON_ALLOWED_TYPES:
        raise ValueError(
            "statement_type must be one of: "
            + ", ".join(STATEMENT_JSON_ALLOWED_TYPES)
        )

    task1_dir = _task1_dir(run_dir)
    model_dir = _statement_model_dir(run_dir)
    paths = {
        "business_driver_map": task1_dir / "business_driver_map.json",
        "source_log": task1_dir / "source_log.json",
        "financial_facts": model_dir / "financial_facts.json",
        "task2_context_packet": model_dir / "task2_context_packet.json",
    }
    artifacts = {name: _read_json_file(path) for name, path in paths.items()}
    missing = [
        _relative_to_workspace(path)
        for name, path in paths.items()
        if artifacts[name] is None
    ]
    return {
        "statement_type": statement_type,
        "run_dir": _relative_to_workspace(run_dir),
        "required_fields": list(STATEMENT_JSON_REQUIRED_FIELDS),
        "canonical_row_keys": list(STATEMENT_CANONICAL_KEYS[statement_type]),
        "cross_statement_dependency_hints": list(
            STATEMENT_DEPENDENCY_HINTS[statement_type]
        ),
        "artifacts": artifacts,
        "missing_artifacts": missing,
    }


def _normalize_statement_type(statement_type: str) -> str:
    aliases = {
        "is": "income_statement",
        "income_statement": "income_statement",
        "bs": "balance_sheet",
        "balance_sheet": "balance_sheet",
        "cf": "cash_flow",
        "cash_flow": "cash_flow",
        "cash_flow_statement": "cash_flow",
    }
    normalized = aliases.get(str(statement_type).strip().lower())
    if normalized is None:
        raise ValueError(
            "statement_type must be one of: income_statement, balance_sheet, cash_flow"
        )
    return normalized


def _canonical_keys(payload: dict[str, Any]) -> set[str]:
    raw = payload.get("canonical_row_keys")
    if isinstance(raw, dict):
        return {str(key) for key in raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    return set()


def _dependency_values(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("cross_statement_dependencies")
    if isinstance(raw, dict):
        values: list[str] = []
        for key, value in raw.items():
            values.append(str(key))
            if isinstance(value, list):
                values.extend(str(item) for item in value)
            elif isinstance(value, dict):
                values.extend(str(item) for item in value.values())
            else:
                values.append(str(value))
        return values
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def _validate_statement_payload(
    payload: dict[str, Any],
    expected_statement_type: str,
) -> dict[str, Any]:
    critical: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    actual_type = payload.get("statement_type")
    if actual_type != expected_statement_type:
        critical.append(
            {
                "category": "Statement Type",
                "issue": (
                    f"statement_type must be '{expected_statement_type}', "
                    f"got '{actual_type}'."
                ),
            }
        )

    for field_name in STATEMENT_JSON_REQUIRED_FIELDS:
        if field_name not in payload:
            critical.append(
                {
                    "category": "Missing Required Field",
                    "issue": f"Missing required field: {field_name}",
                }
            )

    required_keys = set(STATEMENT_CANONICAL_KEYS[expected_statement_type])
    present_keys = _canonical_keys(payload)
    missing_keys = sorted(required_keys - present_keys)
    if missing_keys:
        critical.append(
            {
                "category": "Canonical Row Keys",
                "issue": "Missing canonical row keys: " + ", ".join(missing_keys),
            }
        )

    dependencies = " ".join(_dependency_values(payload)).lower()
    if not dependencies:
        critical.append(
            {
                "category": "Cross Statement Dependencies",
                "issue": "cross_statement_dependencies must declare tie-out links.",
            }
        )
    else:
        for hint in STATEMENT_DEPENDENCY_HINTS[expected_statement_type]:
            if hint.lower() not in dependencies:
                warnings.append(
                    {
                        "category": "Dependency Coverage",
                        "issue": f"Expected dependency hint not found: {hint}",
                    }
                )

    source_coverage = payload.get("source_coverage")
    if not source_coverage:
        critical.append(
            {
                "category": "Source Coverage",
                "issue": "source_coverage is required and cannot be empty.",
            }
        )

    unsourced = payload.get("unsourced_items")
    if unsourced:
        warnings.append(
            {
                "category": "Unsourced Items",
                "issue": f"{len(unsourced)} unsourced item(s) require model_audit.md disclosure.",
            }
        )

    status = "PASS" if not critical else "FAIL"
    return {
        "status": status,
        "statement_type": expected_statement_type,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "critical": critical,
        "warnings": warnings,
    }


def _validate_statement_json(statement_json: str, expected_statement_type: str) -> str:
    payload = _json_loads(statement_json, "statement_json")
    if not isinstance(payload, dict):
        raise ValueError("statement_json must be a JSON object")
    return _json_result(_validate_statement_payload(payload, expected_statement_type))


def _write_statement_json(
    *,
    statement_json: str,
    statement_type: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    payload = _json_loads(statement_json, "statement_json")
    if not isinstance(payload, dict):
        raise ValueError("statement_json must be a JSON object")
    validation = _validate_statement_payload(payload, statement_type)
    if validation["critical_count"]:
        return _json_result(
            {
                "status": "FAIL",
                "statement_type": statement_type,
                "validation": validation,
                "written": [],
            }
        )

    out_dir = _find_run_dir(
        market=market,
        ticker=ticker,
        output_dir=output_dir,
        run_dir=run_dir,
    )
    model_dir = _statement_model_dir(out_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    path = model_dir / STATEMENT_JSON_OUTPUTS[statement_type]
    path.write_text(_json_result(payload) + "\n", encoding="utf-8")
    written.append(_relative_to_workspace(path))

    if statement_type == "income_statement" and isinstance(
        payload.get("revenue_build_spec"),
        dict,
    ):
        revenue_path = model_dir / "revenue_build_spec.json"
        revenue_path.write_text(
            _json_result(payload["revenue_build_spec"]) + "\n",
            encoding="utf-8",
        )
        written.append(_relative_to_workspace(revenue_path))

    return _json_result(
        {
            "status": "OK",
            "statement_type": statement_type,
            "validation": validation,
            "written": written,
        }
    )


def _timestamp() -> str:
    return (
        os.getenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP")
        or datetime.now().strftime("%Y%m%d-%H%M%S")
    )


def _find_run_dir(
    *,
    market: str,
    ticker: str,
    output_dir: str = "./coverage",
    run_dir: str = "",
) -> Path:
    if run_dir:
        return _resolve_workspace_path(run_dir)

    key = f"{_safe_market(market)}:{_safe_ticker(ticker)}:{output_dir}"
    existing = _ACTIVE_RUNS.get(key)
    if existing:
        existing.mkdir(parents=True, exist_ok=True)
        return existing

    return _create_run_dir(
        company="",
        ticker=ticker,
        market=market,
        task_type="unspecified",
        triggering_event="",
        output_dir=output_dir,
    )


def _create_run_dir(
    *,
    company: str,
    ticker: str,
    market: str,
    task_type: str,
    triggering_event: str,
    output_dir: str = "./coverage",
) -> Path:
    coverage_dir = _coverage_dir(market, ticker, output_dir)
    runs_dir = coverage_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    base_timestamp = _timestamp()
    candidate = runs_dir / base_timestamp
    if candidate.exists() and os.getenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP") is None:
        suffix = 2
        while (runs_dir / f"{base_timestamp}-{suffix}").exists():
            suffix += 1
        candidate = runs_dir / f"{base_timestamp}-{suffix}"
    candidate.mkdir(parents=True, exist_ok=True)

    key = f"{_safe_market(market)}:{_safe_ticker(ticker)}:{output_dir}"
    _ACTIVE_RUNS[key] = candidate

    manifest_path = candidate / "run_manifest.json"
    if not manifest_path.exists():
        manifest = {
            "run_id": candidate.name,
            "company": company,
            "ticker": ticker,
            "market": market,
            "task_type": task_type,
            "triggering_event": triggering_event,
            "subagents_called": [],
            "input_artifacts": [],
            "output_artifacts": [],
            "final_conclusion": "",
            "unsourced": [],
            "follow_up_checklist": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    coverage_state = coverage_dir / "coverage_state.json"
    if not coverage_state.exists():
        state = {
            "company": company,
            "ticker": ticker,
            "market": market,
            "coverage_status": "created",
            "latest_run": _relative_to_workspace(candidate),
            "latest_model_path": "",
            "latest_valuation_state": "",
            "latest_price_target": "",
            "latest_rating": "",
            "latest_recommendation": "",
            "latest_thesis_pillars": [],
            "key_assumptions": [],
            "next_catalysts": [],
            "stale_data_flags": [],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        coverage_state.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return candidate


@tool
def create_coverage_run_dir(
    company: str,
    ticker: str,
    market: str,
    task_type: str = "initiation",
    triggering_event: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Create or return a timestamped run directory for one stock coverage task.

    Args:
        company: Company name.
        ticker: Exchange ticker or code.
        market: Listing market, such as A-share, HK, US, or ADR.
        task_type: initiation, update, valuation_refresh, model_audit, etc.
        triggering_event: Optional event that triggered this run.
        output_dir: Coverage root relative to workspace. Defaults to ./coverage.

    Returns:
        JSON with workspace-relative coverage_dir, run_dir, manifest_path, and
        coverage_state_path.
    """
    run_dir = _create_run_dir(
        company=company,
        ticker=ticker,
        market=market,
        task_type=task_type,
        triggering_event=triggering_event,
        output_dir=output_dir,
    )
    coverage_dir = run_dir.parents[1]
    result = {
        "coverage_dir": _relative_to_workspace(coverage_dir),
        "run_dir": _relative_to_workspace(run_dir),
        "manifest_path": _relative_to_workspace(run_dir / "run_manifest.json"),
        "coverage_state_path": _relative_to_workspace(coverage_dir / "coverage_state.json"),
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def write_markdown_artifact(
    markdown: str,
    filename: str,
    subdir: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Write a Markdown artifact into a coverage run subdirectory."""
    out_dir = _find_run_dir(
        market=market,
        ticker=ticker,
        output_dir=output_dir,
        run_dir=run_dir,
    )
    artifact_dir = out_dir / _slugify(subdir, "artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _slugify(Path(filename).stem, "artifact") + ".md"
    path = artifact_dir / safe_name
    path.write_text(markdown, encoding="utf-8")
    return _relative_to_workspace(path)


@tool
def write_json_artifact(
    data_json: str,
    filename: str,
    subdir: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Validate and write a JSON artifact into a coverage run subdirectory."""
    parsed: Any = _json_loads(data_json, "data_json")
    out_dir = _find_run_dir(
        market=market,
        ticker=ticker,
        output_dir=output_dir,
        run_dir=run_dir,
    )
    artifact_dir = out_dir / _slugify(subdir, "artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _slugify(Path(filename).stem, "artifact") + ".json"
    path = artifact_dir / safe_name
    path.write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return _relative_to_workspace(path)


@tool
def read_statement_context(
    statement_type: str,
    run_dir: str,
    output_dir: str = "./coverage",
) -> str:
    """Read minimal Task 2 context for one independent statement JSON modeler.

    Args:
        statement_type: income_statement, balance_sheet, or cash_flow.
        run_dir: Coverage run directory, absolute or workspace-relative.
        output_dir: Coverage root used only when resolving relative paths.

    Returns:
        JSON with Task 1 artifacts, financial_facts.json, optional
        task2_context_packet.json, required fields, canonical keys, and dependency
        hints for the requested statement type.
    """
    del output_dir
    normalized_type = _normalize_statement_type(statement_type)
    out_dir = _resolve_workspace_path(run_dir)
    return _json_result(_statement_context_payload(normalized_type, out_dir))


@tool
def validate_income_statement_json(statement_json: str) -> str:
    """Validate independent Revenue Build and Income Statement JSON specs."""
    return _validate_statement_json(statement_json, "income_statement")


@tool
def write_income_statement_json(
    statement_json: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Validate and write income_statement_spec.json and optional revenue_build_spec.json."""
    return _write_statement_json(
        statement_json=statement_json,
        statement_type="income_statement",
        ticker=ticker,
        market=market,
        run_dir=run_dir,
        output_dir=output_dir,
    )


@tool
def validate_balance_sheet_json(statement_json: str) -> str:
    """Validate independent Balance Sheet JSON spec."""
    return _validate_statement_json(statement_json, "balance_sheet")


@tool
def write_balance_sheet_json(
    statement_json: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Validate and write balance_sheet_spec.json."""
    return _write_statement_json(
        statement_json=statement_json,
        statement_type="balance_sheet",
        ticker=ticker,
        market=market,
        run_dir=run_dir,
        output_dir=output_dir,
    )


@tool
def validate_cash_flow_json(statement_json: str) -> str:
    """Validate independent Cash Flow Statement JSON spec."""
    return _validate_statement_json(statement_json, "cash_flow")


@tool
def write_cash_flow_json(
    statement_json: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Validate and write cash_flow_statement_spec.json."""
    return _write_statement_json(
        statement_json=statement_json,
        statement_type="cash_flow",
        ticker=ticker,
        market=market,
        run_dir=run_dir,
        output_dir=output_dir,
    )


@tool
def update_run_manifest(
    patch_json: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = "./coverage",
) -> str:
    """Merge a JSON patch object into the current run manifest."""
    patch: Any = _json_loads(patch_json, "patch_json")
    if not isinstance(patch, dict):
        raise ValueError("patch_json must be a JSON object")

    out_dir = _find_run_dir(
        market=market,
        ticker=ticker,
        output_dir=output_dir,
        run_dir=run_dir,
    )
    manifest_path = out_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key, value in patch.items():
        if isinstance(value, list) and isinstance(manifest.get(key), list):
            manifest[key].extend(value)
        else:
            manifest[key] = value
    manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return _relative_to_workspace(manifest_path)


@tool
def write_coverage_state(
    state_json: str,
    ticker: str,
    market: str,
    output_dir: str = "./coverage",
) -> str:
    """Overwrite coverage_state.json for the stock after validating JSON."""
    state: Any = _json_loads(state_json, "state_json")
    if not isinstance(state, dict):
        raise ValueError("state_json must be a JSON object")

    coverage_dir = _coverage_dir(market, ticker, output_dir)
    coverage_dir.mkdir(parents=True, exist_ok=True)
    state.setdefault("ticker", ticker)
    state.setdefault("market", market)
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = coverage_dir / "coverage_state.json"
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return _relative_to_workspace(path)
