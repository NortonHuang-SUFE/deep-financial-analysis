"""Local artifact tools for the Single Stock Coverage agent."""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


DEFAULT_OUTPUT_DIR = "./out/coverage"

_ACTIVE_RUNS: dict[str, Path] = {}

TASK1_REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "company_research.md",
    "business_driver_map.json",
    "source_log.json",
)

TASK2_STATEMENT_ARTIFACTS: dict[str, str] = {
    "income_statement": "income_statement_spec.json",
    "balance_sheet": "balance_sheet_spec.json",
    "cash_flow": "cash_flow_statement_spec.json",
}

TASK2_MODEL_ARTIFACTS: tuple[str, ...] = (
    "financial_facts.json",
    "task2_context_packet.json",
    "statement_spec_pack.json",
    "integrated_model.xlsx",
    "model_audit.md",
)

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

THREE_STATEMENT_TABS: tuple[str, ...] = (
    "Cover",
    "Sources",
    "Assumptions",
    "Revenue Build",
    "Income Statement",
    "Balance Sheet",
    "Cash Flow Statement",
    "Working Capital",
    "PP&E & D&A",
    "Debt & Interest",
    "Share Count",
    "DCF Inputs",
    "Checks",
)

REQUIRED_MODEL_NAMES: tuple[str, ...] = (
    "ScenarioSelector",
    "RevDriverBlock",
    "MarginDriverBlock",
    "NWCDriverBlock",
    "CapExDriverBlock",
    "DebtDriverBlock",
)

DEFAULT_THREE_STATEMENT_ROW_MAP: dict[str, dict[str, int]] = {
    "revenue_build": {
        "core_revenue": 10,
        "revenue_total": 12,
        "revenue_growth": 13,
    },
    "income_statement": {
        "revenue_total": 8,
        "cogs": 9,
        "gross_profit": 10,
        "operating_expenses": 12,
        "da_total": 13,
        "ebit": 14,
        "ebitda": 15,
        "interest_expense": 17,
        "pretax_income": 18,
        "tax_expense": 19,
        "net_income": 20,
        "diluted_shares": 22,
        "eps_diluted": 23,
    },
    "balance_sheet": {
        "cash_and_equivalents": 8,
        "accounts_receivable": 9,
        "inventory": 10,
        "total_current_assets": 11,
        "net_ppe": 13,
        "other_assets": 14,
        "total_assets": 15,
        "accounts_payable": 18,
        "total_current_liabilities": 19,
        "total_debt": 20,
        "total_liabilities": 21,
        "common_stock_apic": 24,
        "retained_earnings": 25,
        "total_equity": 26,
        "total_liabilities_and_equity": 27,
    },
    "cash_flow": {
        "net_income_cf": 8,
        "da_addback": 9,
        "nwc_change": 10,
        "cfo_total": 11,
        "capex": 14,
        "cfi_total": 15,
        "debt_issuance": 18,
        "debt_proceeds_repayments": 19,
        "dividends": 20,
        "cff_total": 21,
        "net_change_cash": 23,
        "beginning_cash": 24,
        "ending_cash": 25,
    },
    "working_capital": {
        "accounts_receivable": 8,
        "inventory": 9,
        "accounts_payable": 10,
        "net_working_capital": 11,
        "nwc_change": 12,
    },
    "ppe_da": {
        "beginning_ppe": 8,
        "capex": 9,
        "da_total": 10,
        "ending_ppe": 11,
    },
    "debt_interest": {
        "beginning_debt": 8,
        "debt_issuance": 9,
        "debt_repayment": 10,
        "ending_debt": 11,
        "interest_expense": 12,
    },
    "share_count": {
        "beginning_diluted_shares": 8,
        "share_issuance": 9,
        "buybacks": 10,
        "ending_diluted_shares": 11,
        "dividends": 12,
    },
    "dcf_inputs": {
        "revenue_total": 8,
        "ebit": 9,
        "tax_rate": 10,
        "da_total": 11,
        "capex": 12,
        "nwc_change": 13,
        "total_debt": 14,
        "cash_and_equivalents": 15,
        "diluted_shares": 16,
        "scenario_label": 17,
    },
    "checks": {
        "failing_check_count": 4,
        "bs_balance": 8,
        "cash_tie_out": 9,
        "ni_link": 10,
        "re_roll_forward": 11,
        "capex_ppe_tie": 12,
        "debt_tie": 13,
        "revenue_tie": 14,
        "da_tie": 15,
    },
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    return _project_root().parent


def _resolve_workspace_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return _canonicalize_workspace_path(candidate)
    return _canonicalize_workspace_path(_workspace_root() / candidate)


def _canonicalize_workspace_path(path: Path) -> Path:
    """Map project-local out/ paths to the workspace-level artifact root."""
    project_out = _project_root() / "out"
    try:
        return _workspace_root() / "out" / path.resolve().relative_to(project_out)
    except ValueError:
        return path


def _project_wrong_root_path(path: Path) -> Path | None:
    try:
        rel = path.resolve().relative_to(_workspace_root())
    except ValueError:
        return None
    if not rel.parts or rel.parts[0] != "out":
        return None
    return _project_root() / rel


def _slugify(text: str, fallback: str = "unknown") -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text).strip()).strip("-")
    return normalized.lower() or fallback


def _safe_market(market: str) -> str:
    return _slugify(market or "market", "market")


def _safe_ticker(ticker: str) -> str:
    return _slugify(ticker or "ticker", "ticker")


def _coverage_root(output_dir: str = DEFAULT_OUTPUT_DIR) -> Path:
    return _resolve_workspace_path(output_dir)


def _coverage_dir(market: str, ticker: str, output_dir: str = DEFAULT_OUTPUT_DIR) -> Path:
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


def _field(data: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    cleaned = str(value).replace(",", "").replace("%", "").strip()
    if not cleaned or cleaned.upper() in {"[UNSOURCED]", "UNSOURCED"}:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def _as_decimal(value: Any, default: float = 0.0) -> float:
    parsed = _as_float(value, default)
    return parsed / 100.0 if abs(parsed) > 1.5 else parsed


def _period_year(value: Any, fallback: int) -> int:
    match = re.search(r"(19|20)\d{2}", str(value or ""))
    return int(match.group(0)) if match else fallback


def _column_letter(col_index: int) -> str:
    letters = ""
    while col_index > 0:
        col_index, remainder = divmod(col_index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _sheet_ref(sheet_name: str, cell_ref: str) -> str:
    if " " in sheet_name or "&" in sheet_name:
        return f"'{sheet_name}'!{cell_ref}"
    return f"{sheet_name}!{cell_ref}"


def _formula(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("=")


def _merge_payload_model_input(payload: dict[str, Any]) -> dict[str, Any]:
    facts = payload.get("financial_facts")
    if isinstance(facts, dict):
        merged = dict(facts)
        merged.update(payload)
        return merged
    return payload


def _historical_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("historicals") or payload.get("historical_financials") or []
    if not isinstance(records, list) or not records:
        raise ValueError("model_input_json must include a non-empty historicals list")
    normalized: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"historicals[{idx}] must be a JSON object")
        year = _period_year(record.get("year") or record.get("period"), 2020 + idx)
        label = str(record.get("period") or record.get("label") or f"FY{year}A")
        normalized.append({**record, "year": year, "period": label})
    return sorted(normalized, key=lambda item: item["year"])


def _forecast_labels(payload: dict[str, Any], latest_year: int) -> list[str]:
    raw = payload.get("forecast_years") or payload.get("projection_years_list")
    if isinstance(raw, list) and raw:
        return [
            str(item) if str(item).upper().startswith("FY") else f"FY{item}E"
            for item in raw
        ]
    periods = int(_as_float(payload.get("projection_periods"), 2))
    periods = max(1, min(periods, 7))
    return [f"FY{latest_year + offset}E" for offset in range(1, periods + 1)]


def _source_for(record: dict[str, Any]) -> str:
    source = _field(record, "source", "sources", "source_text", default="[UNSOURCED]")
    if isinstance(source, list):
        return "; ".join(str(item) for item in source) or "[UNSOURCED]"
    return str(source or "[UNSOURCED]")


def _latest_ratio(numerator: float, denominator: float, default: float) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def _model_metadata(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "company": str(_field(payload, "company", "company_name", default="Company")),
        "ticker": str(_field(payload, "ticker", "symbol", default="TICKER")),
        "market": str(_field(payload, "market", "exchange", default="")),
        "currency": str(_field(payload, "currency", "reporting_currency", default="USD")),
        "unit": str(_field(payload, "unit", "reporting_unit", default="millions")),
        "fiscal_year_end": str(_field(payload, "fiscal_year_end", default="Dec")),
    }


def _historical_value(record: dict[str, Any], key: str) -> float:
    aliases: dict[str, tuple[str, ...]] = {
        "revenue": ("revenue", "revenue_total", "net_revenue"),
        "gross_profit": ("gross_profit",),
        "operating_expenses": ("operating_expenses", "opex", "sgna"),
        "da": ("da", "d_and_a", "depreciation_amortization"),
        "ebit": ("ebit", "operating_income"),
        "ebitda": ("ebitda",),
        "interest_expense": ("interest_expense", "interest"),
        "pretax_income": ("pretax_income", "ebt", "income_before_tax"),
        "tax_expense": ("tax_expense", "tax"),
        "net_income": ("net_income",),
        "cash": ("cash", "cash_and_equivalents"),
        "ar": ("accounts_receivable", "ar"),
        "inventory": ("inventory",),
        "ap": ("accounts_payable", "ap"),
        "capex": ("capex", "capital_expenditures"),
        "ppe": ("ppe", "net_ppe", "property_plant_equipment"),
        "debt": ("debt", "total_debt"),
        "retained_earnings": ("retained_earnings",),
        "shares": ("diluted_shares", "shares_outstanding", "shares"),
    }
    return _as_float(_field(record, *aliases.get(key, (key,))), 0.0)


def _assumption_set(payload: dict[str, Any], latest: dict[str, Any]) -> dict[str, float]:
    assumptions = payload.get("assumptions")
    if not isinstance(assumptions, dict):
        assumptions = {}
    revenue = _historical_value(latest, "revenue")
    gross_profit = _historical_value(latest, "gross_profit") or revenue * 0.5
    opex = _historical_value(latest, "operating_expenses")
    da = _historical_value(latest, "da")
    capex = abs(_historical_value(latest, "capex"))
    pretax = _historical_value(latest, "pretax_income")
    tax = _historical_value(latest, "tax_expense")
    return {
        "revenue_growth": _as_decimal(assumptions.get("revenue_growth"), 0.05),
        "gross_margin": _as_decimal(
            assumptions.get("gross_margin"),
            _latest_ratio(gross_profit, revenue, 0.5),
        ),
        "opex_pct_revenue": _as_decimal(
            assumptions.get("opex_pct_revenue"),
            _latest_ratio(opex, revenue, 0.2),
        ),
        "tax_rate": _as_decimal(
            assumptions.get("tax_rate"),
            _latest_ratio(tax, pretax, 0.25),
        ),
        "ar_days": _as_float(assumptions.get("ar_days"), 45.0),
        "inventory_pct_revenue": _as_decimal(
            assumptions.get("inventory_pct_revenue"),
            0.1,
        ),
        "ap_days": _as_float(assumptions.get("ap_days"), 30.0),
        "da_pct_revenue": _as_decimal(
            assumptions.get("da_pct_revenue"),
            _latest_ratio(da, revenue, 0.03),
        ),
        "capex_pct_revenue": _as_decimal(
            assumptions.get("capex_pct_revenue"),
            _latest_ratio(capex, revenue, 0.04),
        ),
        "interest_rate": _as_decimal(assumptions.get("interest_rate"), 0.05),
        "debt_repayment_pct": _as_decimal(
            assumptions.get("debt_repayment_pct"),
            0.0,
        ),
        "diluted_shares_growth": _as_decimal(
            assumptions.get("diluted_shares_growth"),
            0.0,
        ),
        "dividend_payout_pct": _as_decimal(
            assumptions.get("dividend_payout_pct"),
            0.0,
        ),
    }


def _validation_result(
    status: str,
    critical: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> str:
    return _json_result(
        {
            "status": status,
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "critical": critical,
            "warnings": warnings,
        }
    )


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


def _required_task1_paths(run_dir: Path) -> dict[str, Path]:
    task1_dir = _task1_dir(run_dir)
    return {name: task1_dir / name for name in TASK1_REQUIRED_ARTIFACTS}


def _task1_missing_paths(run_dir: Path) -> list[str]:
    return [
        _relative_to_workspace(path)
        for path in _required_task1_paths(run_dir).values()
        if not path.exists()
    ]


def _infer_run_dir_from_task1_path(path: Path) -> Path:
    if path.name in TASK1_REQUIRED_ARTIFACTS:
        path = path.parent
    return path.parent if path.name == "01_company_research" else path


def _latest_task1_run(
    *,
    ticker: str,
    market: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Path | None:
    runs_dir = _coverage_dir(market, ticker, output_dir) / "runs"
    if not runs_dir.exists():
        return None
    candidates = [
        path
        for path in runs_dir.iterdir()
        if path.is_dir() and not _task1_missing_paths(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.name)[-1]


def _wrong_root_artifacts_for(run_dir: Path) -> list[dict[str, str]]:
    wrong_run_dir = _project_wrong_root_path(run_dir)
    if wrong_run_dir is None or not wrong_run_dir.exists():
        return []

    artifacts: list[dict[str, str]] = []
    tracked = [
        *(wrong_run_dir / "01_company_research" / name for name in TASK1_REQUIRED_ARTIFACTS),
        *(
            wrong_run_dir / "02_financial_model" / name
            for name in (
                *TASK2_STATEMENT_ARTIFACTS.values(),
                "revenue_build_spec.json",
                *TASK2_MODEL_ARTIFACTS,
            )
        ),
    ]
    for wrong_path in tracked:
        if not wrong_path.exists():
            continue
        canonical_path = _workspace_root() / wrong_path.relative_to(_project_root())
        severity = "critical" if not canonical_path.exists() else "warning"
        artifacts.append(
            {
                "severity": severity,
                "wrong_root_path": str(wrong_path),
                "canonical_path": _relative_to_workspace(canonical_path),
            }
        )
    return artifacts


def _artifact_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": _relative_to_workspace(path),
        "exists": path.exists(),
    }
    if path.suffix == ".json" and path.exists():
        try:
            parsed = _read_json_file(path)
        except Exception as exc:
            record.update({"json_valid": False, "error": str(exc)})
        else:
            record["json_valid"] = isinstance(parsed, (dict, list))
    return record


def _append_finding(
    findings: list[dict[str, str]],
    *,
    category: str,
    issue: str,
    path: Path | None = None,
) -> None:
    finding = {"category": category, "issue": issue}
    if path is not None:
        finding["path"] = _relative_to_workspace(path)
    findings.append(finding)


def _safe_audit_text(value: Any, limit: int = 700) -> str:
    text = str(value or "").replace("\r", " ").strip()
    blocked = (
        "SystemMessage",
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
        "inputs.messages",
        '"messages"',
        '"generations"',
        "langchain.schema.messages",
    )
    if any(token in text for token in blocked):
        return "[omitted runtime trace]"
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def _normalize_findings(raw: Any, *, limit: int = 50) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    findings: list[dict[str, str]] = []
    for item in raw[:limit]:
        if isinstance(item, dict):
            category = _safe_audit_text(item.get("category") or item.get("type") or "Finding")
            issue = _safe_audit_text(item.get("issue") or item.get("message") or item)
            path = _safe_audit_text(item.get("path") or "")
            finding = {"category": category, "issue": issue}
            if path:
                finding["path"] = path
        else:
            finding = {"category": "Finding", "issue": _safe_audit_text(item)}
        findings.append(finding)
    return findings


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
        "company_research": task1_dir / "company_research.md",
    }
    optional_paths = {
        "financial_facts": model_dir / "financial_facts.json",
        "task2_context_packet": model_dir / "task2_context_packet.json",
    }
    artifacts = {
        name: (
            path.read_text(encoding="utf-8")
            if name == "company_research" and path.exists()
            else _read_json_file(path)
        )
        for name, path in paths.items()
    }
    artifacts.update({name: _read_json_file(path) for name, path in optional_paths.items()})
    missing = [
        _relative_to_workspace(path)
        for name, path in paths.items()
        if artifacts[name] is None
    ]
    optional_missing = [
        _relative_to_workspace(path)
        for name, path in optional_paths.items()
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
        "optional_missing_artifacts": optional_missing,
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


def _supplemental_keys(payload: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    raw = payload.get("supplemental_line_items") or []
    if isinstance(raw, dict):
        raw = list(raw.values())
    if not isinstance(raw, list):
        return keys
    for item in raw:
        if isinstance(item, dict):
            key = _field(
                item,
                "canonical_key",
                "line_item_key",
                "key",
                "name",
                default="",
            )
            if key:
                keys.add(str(key))
        elif item:
            keys.add(str(item))
    return keys


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


def _historical_input_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("historical_inputs")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _historical_input_key(record: dict[str, Any]) -> str:
    return str(
        _field(
            record,
            "canonical_key",
            "canonical_row_key",
            "line_item_key",
            "key",
            "name",
            default="",
        )
        or ""
    )


def _model_field_for_canonical_key(canonical_key: str) -> str | None:
    mapping = {
        "revenue_total": "revenue",
        "gross_profit": "gross_profit",
        "ebit": "ebit",
        "ebitda": "ebitda",
        "interest_expense": "interest_expense",
        "pretax_income": "pretax_income",
        "tax_expense": "tax_expense",
        "net_income": "net_income",
        "da_total": "da",
        "cash_and_equivalents": "cash",
        "accounts_receivable": "ar",
        "inventory": "inventory",
        "accounts_payable": "ap",
        "capex": "capex",
        "net_ppe": "ppe",
        "total_debt": "debt",
        "retained_earnings": "retained_earnings",
        "diluted_shares": "shares",
    }
    return mapping.get(canonical_key)


def _validate_statement_historical_inputs(
    payload: dict[str, Any],
    expected_statement_type: str,
    critical: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    records = _historical_input_records(payload)
    if not records:
        critical.append(
            {
                "category": "Historical Inputs",
                "issue": "historical_inputs must include sourced records.",
            }
        )
        return

    canonical_keys = _canonical_keys(payload)
    supplemental_keys = _supplemental_keys(payload)
    for idx, record in enumerate(records):
        missing: list[str] = []
        if not record.get("period"):
            missing.append("period")
        key = _historical_input_key(record)
        if not key:
            missing.append("canonical_key")
        elif key not in canonical_keys:
            parent_key = str(
                _field(
                    record,
                    "parent_canonical_key",
                    "parent_key",
                    "aggregate_key",
                    default="",
                )
                or ""
            )
            if parent_key in canonical_keys or key in supplemental_keys:
                pass
            else:
                warnings.append(
                    {
                        "category": "Historical Inputs",
                        "issue": (
                            f"historical_inputs[{idx}] canonical_key '{key}' is not "
                            f"listed in {expected_statement_type} canonical_row_keys "
                            "and has no valid parent_canonical_key."
                        ),
                    }
                )
        if "value" not in record and "amount" not in record:
            missing.append("value")
        if not _field(record, "source", "source_text", default=""):
            missing.append("source")
        if missing:
            critical.append(
                {
                    "category": "Historical Inputs",
                    "issue": (
                        f"historical_inputs[{idx}] missing required field(s): "
                        + ", ".join(missing)
                    ),
                }
            )


def _derive_financial_facts(
    *,
    specs: dict[str, dict[str, Any]],
    ticker: str,
    market: str,
) -> dict[str, Any]:
    metadata_source = next(iter(specs.values()), {})
    periods: dict[str, dict[str, Any]] = {}
    sources: list[str] = []
    unsourced: list[str] = []

    for statement_type, payload in specs.items():
        for item in _historical_input_records(payload):
            period = str(item.get("period") or "")
            if not period:
                continue
            record = periods.setdefault(
                period,
                {
                    "period": period,
                    "year": _period_year(period, 2020 + len(periods)),
                    "source": "[UNSOURCED]",
                },
            )
            source = str(_field(item, "source", "source_text", default="[UNSOURCED]"))
            if source and source != "[UNSOURCED]":
                sources.append(source)
                if record.get("source") == "[UNSOURCED]":
                    record["source"] = source
            elif source == "[UNSOURCED]":
                unsourced.append(f"{statement_type}:{period}:{_historical_input_key(item)}")

            model_field = _model_field_for_canonical_key(_historical_input_key(item))
            if not model_field:
                parent_key = str(
                    _field(
                        item,
                        "parent_canonical_key",
                        "parent_key",
                        "aggregate_key",
                        default="",
                    )
                    or ""
                )
                model_field = _model_field_for_canonical_key(parent_key)
            if model_field:
                record[model_field] = _as_float(
                    _field(item, "value", "amount", default=0.0),
                    0.0,
                )

        for item in payload.get("unsourced_items") or []:
            unsourced.append(f"{statement_type}:{item}")

    historicals = sorted(periods.values(), key=lambda item: item["year"])
    return {
        "company": str(_field(metadata_source, "company", "company_name", default="Company")),
        "ticker": str(_field(metadata_source, "ticker", "symbol", default=ticker)),
        "market": str(_field(metadata_source, "market", "exchange", default=market)),
        "currency": str(_field(metadata_source, "currency", "reporting_currency", default="USD")),
        "unit": str(_field(metadata_source, "unit", "reporting_unit", default="millions")),
        "fiscal_year_end": str(_field(metadata_source, "fiscal_year_end", default="Dec")),
        "historicals": historicals,
        "segments": [],
        "guidance": [],
        "projection_summary": {},
        "assumptions": dict(metadata_source.get("assumptions") or {}),
        "sources": sorted(set(sources)),
        "unsourced": sorted(set(unsourced)),
    }


def _derive_task2_context_packet(
    *,
    specs: dict[str, dict[str, Any]],
    pack: dict[str, Any],
    financial_facts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "company": financial_facts.get("company", "Company"),
        "ticker": financial_facts.get("ticker", ""),
        "market": financial_facts.get("market", ""),
        "currency": financial_facts.get("currency", "USD"),
        "unit": financial_facts.get("unit", "millions"),
        "fiscal_year_end": financial_facts.get("fiscal_year_end", "Dec"),
        "periods": [item.get("period") for item in financial_facts.get("historicals", [])],
        "canonical_row_keys": {
            statement_type: list(STATEMENT_CANONICAL_KEYS[statement_type])
            for statement_type in STATEMENT_JSON_ALLOWED_TYPES
        },
        "source_coverage": {
            statement_type: payload.get("source_coverage", {})
            for statement_type, payload in specs.items()
        },
        "unsourced": financial_facts.get("unsourced", []),
        "reconciliation_status": pack.get("status"),
        "critical_count": pack.get("critical_count", 0),
        "warning_count": pack.get("warning_count", 0),
    }


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

    _validate_statement_historical_inputs(
        payload,
        expected_statement_type,
        critical,
        warnings,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Create or return a timestamped run directory for one stock coverage task.

    Args:
        company: Company name.
        ticker: Exchange ticker or code.
        market: Listing market, such as A-share, HK, US, or ADR.
        task_type: initiation, update, valuation_refresh, model_audit, etc.
        triggering_event: Optional event that triggered this run.
        output_dir: Coverage root relative to workspace. Defaults to ./out/coverage.

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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
def resolve_task2_handoff(
    ticker: str,
    market: str,
    run_dir: str = "",
    task1_dir: str = "",
    company_research_path: str = "",
    business_driver_map_path: str = "",
    source_log_path: str = "",
    create_new_run: bool = False,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Resolve Task 2 to one canonical workspace-level run directory.

    Direct Task 2 runs should continue the run that already contains Task 1
    artifacts. This tool never reconstructs Task 1 from prose. It either finds
    real Task 1 files or returns a blocking failure with exact missing paths.
    """
    explicit_paths = [
        company_research_path,
        business_driver_map_path,
        source_log_path,
    ]
    supplied = [path for path in explicit_paths if path]

    selected_run_dir: Path | None = None
    source = ""
    if run_dir:
        selected_run_dir = _infer_run_dir_from_task1_path(_resolve_workspace_path(run_dir))
        source = "run_dir"
    elif task1_dir:
        selected_run_dir = _infer_run_dir_from_task1_path(
            _resolve_workspace_path(task1_dir)
        )
        source = "task1_dir"
    elif supplied:
        selected_run_dir = _infer_run_dir_from_task1_path(
            _resolve_workspace_path(supplied[0])
        )
        source = "task1_file_paths"
    elif create_new_run:
        selected_run_dir = _create_run_dir(
            company="",
            ticker=ticker,
            market=market,
            task_type="initiation",
            triggering_event="",
            output_dir=output_dir,
        )
        source = "created_new_run"
    else:
        selected_run_dir = _latest_task1_run(
            ticker=ticker,
            market=market,
            output_dir=output_dir,
        )
        source = "latest_task1_run"

    if selected_run_dir is None:
        coverage_runs = _coverage_dir(market, ticker, output_dir) / "runs"
        return _json_result(
            {
                "status": "FAIL",
                "ticker": ticker,
                "market": market,
                "run_dir": "",
                "missing_artifacts": [
                    f"No run with complete Task 1 artifacts under {_relative_to_workspace(coverage_runs)}"
                ],
                "created_new_run": False,
                "source": source,
            }
        )

    selected_run_dir = _canonicalize_workspace_path(selected_run_dir)
    missing = _task1_missing_paths(selected_run_dir)
    file_path_mismatches: list[str] = []
    for supplied_path, expected_name in zip(explicit_paths, TASK1_REQUIRED_ARTIFACTS):
        if not supplied_path:
            continue
        resolved = _resolve_workspace_path(supplied_path)
        expected = _task1_dir(selected_run_dir) / expected_name
        if resolved.resolve() != expected.resolve():
            file_path_mismatches.append(
                f"{expected_name}: expected {_relative_to_workspace(expected)}, "
                f"got {_relative_to_workspace(resolved)}"
            )

    key = f"{_safe_market(market)}:{_safe_ticker(ticker)}:{output_dir}"
    _ACTIVE_RUNS[key] = selected_run_dir

    wrong_root_artifacts = _wrong_root_artifacts_for(selected_run_dir)
    status = "OK" if not missing and not file_path_mismatches else "FAIL"
    return _json_result(
        {
            "status": status,
            "ticker": ticker,
            "market": market,
            "run_dir": _relative_to_workspace(selected_run_dir),
            "task1_dir": _relative_to_workspace(_task1_dir(selected_run_dir)),
            "model_dir": _relative_to_workspace(_statement_model_dir(selected_run_dir)),
            "missing_artifacts": missing,
            "file_path_mismatches": file_path_mismatches,
            "wrong_root_artifacts": wrong_root_artifacts,
            "created_new_run": source == "created_new_run",
            "source": source,
        }
    )


@tool
def verify_task2_artifacts(run_dir: str, stage: str = "all") -> str:
    """Verify Task 2 artifacts in the canonical run directory.

    Args:
        run_dir: Coverage run directory, absolute or workspace-relative.
        stage: task1, financial_facts, statements, reconciliation, workbook, or all.
    """
    out_dir = _resolve_workspace_path(run_dir)
    model_dir = _statement_model_dir(out_dir)
    normalized_stage = str(stage or "all").strip().lower()
    critical: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    artifacts: dict[str, Any] = {}

    valid_stages = {
        "task1",
        "financial_facts",
        "statements",
        "reconciliation",
        "workbook",
        "all",
    }
    if normalized_stage not in valid_stages:
        raise ValueError("stage must be one of: " + ", ".join(sorted(valid_stages)))

    def should_check(name: str) -> bool:
        return normalized_stage in {"all", name}

    wrong_root_artifacts = _wrong_root_artifacts_for(out_dir)
    for item in wrong_root_artifacts:
        target = critical if item["severity"] == "critical" else warnings
        target.append(
            {
                "category": "Wrong Artifact Root",
                "issue": (
                    "Artifact exists under single-stock-coverage/out instead of "
                    "workspace-level out."
                ),
                "path": item["wrong_root_path"],
            }
        )

    if should_check("task1"):
        artifacts["task1"] = {}
        for name, path in _required_task1_paths(out_dir).items():
            artifacts["task1"][name] = _artifact_record(path)
            if not path.exists():
                _append_finding(
                    critical,
                    category="Missing Task 1 Artifact",
                    issue=f"Required Task 1 artifact missing: {name}",
                    path=path,
                )

    if should_check("financial_facts"):
        artifacts["financial_facts"] = {}
        for name in ("financial_facts.json", "task2_context_packet.json"):
            path = model_dir / name
            artifacts["financial_facts"][name] = _artifact_record(path)
            payload = _read_json_file(path)
            if not isinstance(payload, dict):
                _append_finding(
                    critical,
                    category="Missing Financial Context",
                    issue=f"{name} must exist and be valid JSON before statement modeling.",
                    path=path,
                )
        facts = _read_json_file(model_dir / "financial_facts.json")
        if isinstance(facts, dict) and not isinstance(facts.get("historicals"), list):
            _append_finding(
                critical,
                category="Invalid Financial Facts",
                issue="financial_facts.json must include a historicals list.",
                path=model_dir / "financial_facts.json",
            )

    if should_check("statements"):
        artifacts["statements"] = {}
        for statement_type, filename in TASK2_STATEMENT_ARTIFACTS.items():
            path = model_dir / filename
            artifacts["statements"][statement_type] = _artifact_record(path)
            payload = _read_json_file(path)
            if not isinstance(payload, dict):
                _append_finding(
                    critical,
                    category="Missing Statement JSON",
                    issue=f"{filename} must be written by its statement subagent.",
                    path=path,
                )
                continue
            validation = _validate_statement_payload(payload, statement_type)
            for finding in validation["critical"]:
                critical.append({"statement_type": statement_type, **finding})
            for finding in validation["warnings"]:
                warnings.append({"statement_type": statement_type, **finding})

    if should_check("reconciliation"):
        path = model_dir / "statement_spec_pack.json"
        artifacts["reconciliation"] = {"statement_spec_pack.json": _artifact_record(path)}
        pack = _read_json_file(path)
        if not isinstance(pack, dict):
            _append_finding(
                critical,
                category="Missing Reconciliation",
                issue="statement_spec_pack.json must exist before workbook build.",
                path=path,
            )
        else:
            for finding in pack.get("critical") or []:
                critical.append({"statement_type": "statement_pack", **finding})
            for finding in pack.get("warnings") or []:
                warnings.append({"statement_type": "statement_pack", **finding})

    if should_check("workbook"):
        artifacts["workbook"] = {}
        for name in ("integrated_model.xlsx", "model_audit.md"):
            path = model_dir / name
            artifacts["workbook"][name] = _artifact_record(path)
            if not path.exists():
                _append_finding(
                    critical,
                    category="Missing Workbook Artifact",
                    issue=f"{name} is required for Task 3 handoff.",
                    path=path,
                )

    status = "PASS" if not critical else "FAIL"
    return _json_result(
        {
            "status": status,
            "stage": normalized_stage,
            "run_dir": _relative_to_workspace(out_dir),
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "critical": critical,
            "warnings": warnings,
            "artifacts": artifacts,
            "wrong_root_artifacts": wrong_root_artifacts,
        }
    )


@tool
def write_task2_model_audit(run_dir: str, audit_json: str) -> str:
    """Write a compact Task 2 model_audit.md from structured findings only."""
    audit = _json_loads(audit_json, "audit_json")
    if not isinstance(audit, dict):
        raise ValueError("audit_json must be a JSON object")

    out_dir = _resolve_workspace_path(run_dir)
    model_dir = _statement_model_dir(out_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / "model_audit.md"

    status = _safe_audit_text(audit.get("status") or "UNKNOWN", 80)
    route = _safe_audit_text(audit.get("route") or audit.get("model_route") or "")
    handoff_ready = bool(audit.get("task3_handoff_ready"))
    critical = _normalize_findings(audit.get("critical"))
    warnings = _normalize_findings(audit.get("warnings"))
    artifacts = audit.get("artifacts") if isinstance(audit.get("artifacts"), dict) else {}
    next_steps = [
        _safe_audit_text(item, 300)
        for item in (audit.get("next_steps") or [])
        if _safe_audit_text(item, 300)
    ][:12]

    lines = [
        "# Task 2 Model Audit",
        "",
        f"- Status: {status}",
        f"- Run: `{_relative_to_workspace(out_dir)}`",
        f"- Task 3 handoff ready: {'yes' if handoff_ready else 'no'}",
    ]
    if route:
        lines.append(f"- Route: {route}")
    lines.extend(
        [
            f"- Critical findings: {len(critical)}",
            f"- Warnings: {len(warnings)}",
            "",
            "## Critical Findings",
        ]
    )
    if critical:
        for idx, finding in enumerate(critical, start=1):
            path_text = f" (`{finding['path']}`)" if finding.get("path") else ""
            lines.append(
                f"{idx}. {finding['category']}: {finding['issue']}{path_text}"
            )
    else:
        lines.append("None.")

    lines.extend(["", "## Warnings"])
    if warnings:
        for idx, finding in enumerate(warnings[:50], start=1):
            path_text = f" (`{finding['path']}`)" if finding.get("path") else ""
            lines.append(
                f"{idx}. {finding['category']}: {finding['issue']}{path_text}"
            )
    else:
        lines.append("None.")

    lines.extend(["", "## Artifact Status"])
    if artifacts:
        for name, value in artifacts.items():
            lines.append(f"- `{_safe_audit_text(name, 120)}`: {_safe_audit_text(value, 240)}")
    else:
        lines.append("No artifact status supplied.")

    lines.extend(["", "## Next Steps"])
    if next_steps:
        for idx, item in enumerate(next_steps, start=1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("No follow-up steps supplied.")

    markdown = "\n".join(lines).strip() + "\n"
    path.write_text(markdown, encoding="utf-8")
    return _json_result(
        {
            "status": "OK",
            "model_audit_path": _relative_to_workspace(path),
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "task3_handoff_ready": handoff_ready,
        }
    )


@tool
def read_statement_context(
    statement_type: str,
    run_dir: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
def reconcile_statement_specs(
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Reconcile independent IS, BS, and CF JSON specs before workbook build.

    Reads the three Task 2 statement JSON artifacts, checks canonical row keys,
    source gaps, and cross-statement dependencies, then writes
    `02_financial_model/statement_spec_pack.json`.
    """
    out_dir = _find_run_dir(
        market=market,
        ticker=ticker,
        output_dir=output_dir,
        run_dir=run_dir,
    )
    model_dir = _statement_model_dir(out_dir)
    paths = {
        "income_statement": model_dir / "income_statement_spec.json",
        "balance_sheet": model_dir / "balance_sheet_spec.json",
        "cash_flow": model_dir / "cash_flow_statement_spec.json",
    }
    specs: dict[str, dict[str, Any]] = {}
    critical: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for statement_type, path in paths.items():
        payload = _read_json_file(path)
        if not isinstance(payload, dict):
            critical.append(
                {
                    "statement_type": statement_type,
                    "category": "Missing Statement JSON",
                    "issue": f"Required statement JSON not found: {_relative_to_workspace(path)}",
                }
            )
            continue
        specs[statement_type] = payload
        validation = _validate_statement_payload(payload, statement_type)
        critical.extend(
            {
                "statement_type": statement_type,
                **finding,
            }
            for finding in validation["critical"]
        )
        warnings.extend(
            {
                "statement_type": statement_type,
                **finding,
            }
            for finding in validation["warnings"]
        )

    if len(specs) == 3:
        dependency_text = {
            name: " ".join(_dependency_values(payload)).lower()
            for name, payload in specs.items()
        }
        cross_checks = {
            "IS net income -> CF net income": (
                "income_statement.net_income" in dependency_text["cash_flow"]
            ),
            "CF ending cash -> BS cash": (
                "cash_flow.ending_cash" in dependency_text["balance_sheet"]
            ),
            "RE roll-forward dependency": (
                "income_statement.net_income" in dependency_text["balance_sheet"]
                and "dividends" in dependency_text["balance_sheet"]
            ),
            "DCF revenue dependency": (
                "revenue_total" in " ".join(_canonical_keys(specs["income_statement"]))
            ),
            "DCF debt/cash dependency": (
                "total_debt" in " ".join(_canonical_keys(specs["balance_sheet"]))
                and "cash_and_equivalents" in " ".join(
                    _canonical_keys(specs["balance_sheet"])
                )
            ),
            "DCF cash flow dependency": (
                "capex" in " ".join(_canonical_keys(specs["cash_flow"]))
                and "nwc_change" in " ".join(_canonical_keys(specs["cash_flow"]))
            ),
        }
        for check_name, passed in cross_checks.items():
            if not passed:
                critical.append(
                    {
                        "statement_type": "statement_pack",
                        "category": "Cross Statement Tie",
                        "issue": f"Failed reconciliation check: {check_name}",
                    }
                )

        for statement_type, payload in specs.items():
            if payload.get("unsourced_items"):
                warnings.append(
                    {
                        "statement_type": statement_type,
                        "category": "Source Gap",
                        "issue": (
                            f"{statement_type} has {len(payload['unsourced_items'])} "
                            "unsourced item(s) to disclose in model_audit.md."
                        ),
                    }
                )
            forecast_logic = json.dumps(
                payload.get("forecast_logic", {}),
                ensure_ascii=False,
            ).lower()
            if "hardcode" in forecast_logic and "no hardcode" not in forecast_logic:
                warnings.append(
                    {
                        "statement_type": statement_type,
                        "category": "Forecast Hardcode Risk",
                        "issue": "forecast_logic mentions hardcode; parent must review before builder.",
                    }
                )

    status = "PASS" if not critical else "FAIL"
    pack = {
        "status": status,
        "run_dir": _relative_to_workspace(out_dir),
        "statement_specs": specs,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "critical": critical,
        "warnings": warnings,
        "builder_blocked": bool(critical),
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    pack_path = model_dir / "statement_spec_pack.json"
    pack_path.write_text(_json_result(pack) + "\n", encoding="utf-8")

    facts_path = model_dir / "financial_facts.json"
    context_path = model_dir / "task2_context_packet.json"
    financial_facts = _read_json_file(facts_path)
    if not isinstance(financial_facts, dict):
        financial_facts = _derive_financial_facts(
            specs=specs,
            ticker=ticker,
            market=market,
        )
    context_packet = _read_json_file(context_path)
    if not isinstance(context_packet, dict):
        context_packet = _derive_task2_context_packet(
            specs=specs,
            pack=pack,
            financial_facts=financial_facts,
        )
    else:
        context_packet = {
            **context_packet,
            "reconciliation_status": pack.get("status"),
            "critical_count": pack.get("critical_count", 0),
            "warning_count": pack.get("warning_count", 0),
        }
    facts_path.write_text(_json_result(financial_facts) + "\n", encoding="utf-8")
    context_path.write_text(_json_result(context_packet) + "\n", encoding="utf-8")

    return _json_result(
        {
            **pack,
            "statement_spec_pack_path": _relative_to_workspace(pack_path),
            "financial_facts_path": _relative_to_workspace(facts_path),
            "task2_context_packet_path": _relative_to_workspace(context_path),
        }
    )


def _scoped_build_integrated_three_statement_model_reference(
    model_input_json: str,
    run_dir: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Build deterministic Task 2 integrated_model.xlsx from reconciled inputs."""
    try:
        import openpyxl
        from openpyxl.comments import Comment
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.workbook.defined_name import DefinedName
    except ImportError as exc:
        return _json_result(
            {"status": "ERROR", "message": f"openpyxl is not installed: {exc}"}
        )

    payload = _json_loads(model_input_json, "model_input_json")
    if not isinstance(payload, dict):
        raise ValueError("model_input_json must be a JSON object")

    merged = _merge_payload_model_input(payload)
    metadata = _model_metadata(merged)
    out_dir = (
        _resolve_workspace_path(run_dir)
        if run_dir
        else _find_run_dir(
            market=metadata["market"] or "market",
            ticker=metadata["ticker"],
            output_dir=output_dir,
        )
    )
    model_dir = _statement_model_dir(out_dir)
    pack = _read_json_file(model_dir / "statement_spec_pack.json")
    if isinstance(pack, dict) and pack.get("builder_blocked"):
        return _json_result(
            {
                "status": "FAIL",
                "run_dir": _relative_to_workspace(out_dir),
                "workbook_path": "",
                "critical_count": int(pack.get("critical_count") or 0),
                "warning_count": int(pack.get("warning_count") or 0),
                "critical": pack.get("critical") or [],
                "warnings": pack.get("warnings") or [],
                "message": "statement_spec_pack.json has critical findings; builder is blocked.",
            }
        )

    historicals = _historical_records(merged)
    latest = historicals[-1]
    forecast_labels = _forecast_labels(merged, latest["year"])
    assumptions = _assumption_set(merged, latest)

    model_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = model_dir / "integrated_model.xlsx"

    periods: list[dict[str, Any]] = [
        {"label": record["period"], "record": record, "is_actual": True}
        for record in historicals
    ]
    periods.extend(
        {"label": label, "record": {}, "is_actual": False}
        for label in forecast_labels
    )
    first_col = 3
    last_col = first_col + len(periods) - 1
    actual_count = len(historicals)
    period_columns = {
        str(period["label"]): _column_letter(idx)
        for idx, period in enumerate(periods, start=first_col)
    }
    row_map = json.loads(json.dumps(DEFAULT_THREE_STATEMENT_ROW_MAP))

    styles = {
        "section": PatternFill("solid", fgColor="1F4E79"),
        "header": PatternFill("solid", fgColor="D9E1F2"),
        "input": PatternFill("solid", fgColor="EAF3F8"),
        "white": Font(name="Arial", bold=True, color="FFFFFF", size=11),
        "bold": Font(name="Arial", bold=True, color="000000", size=11),
        "input_font": Font(name="Arial", color="0000FF", size=11),
        "formula": Font(name="Arial", color="000000", size=11),
        "link": Font(name="Arial", color="008000", size=11),
        "normal": Font(name="Arial", color="000000", size=11),
        "center": Alignment(horizontal="center", vertical="center"),
        "left": Alignment(horizontal="left", vertical="center"),
        "border": Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        ),
    }

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheets = {name: wb.create_sheet(name) for name in THREE_STATEMENT_TABS}

    def set_title(ws, title: str) -> None:
        ws["A1"] = title
        ws["A1"].fill = styles["section"]
        ws["A1"].font = styles["white"]
        ws["A1"].alignment = styles["left"]
        ws.merge_cells(
            start_row=1,
            start_column=1,
            end_row=1,
            end_column=max(last_col, 6),
        )
        ws["A3"] = f"Currency: {metadata['currency']} | Unit: {metadata['unit']}"

    def set_period_headers(ws) -> None:
        ws["A5"] = "Line Item"
        ws["B5"] = "Source / Type"
        for cell_ref in ("A5", "B5"):
            ws[cell_ref].fill = styles["header"]
            ws[cell_ref].font = styles["bold"]
        for idx, period in enumerate(periods, start=first_col):
            type_cell = ws.cell(
                row=4,
                column=idx,
                value="Actual" if period["is_actual"] else "Forecast",
            )
            type_cell.font = styles["bold"]
            type_cell.alignment = styles["center"]
            header_cell = ws.cell(row=5, column=idx, value=period["label"])
            header_cell.fill = styles["header"]
            header_cell.font = styles["bold"]
            header_cell.alignment = styles["center"]

    def format_sheet(ws) -> None:
        ws.freeze_panes = "C6"
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 20
        for col in range(first_col, last_col + 1):
            ws.column_dimensions[_column_letter(col)].width = 14
        for row in ws.iter_rows():
            for cell in row:
                cell.border = styles["border"]
                cell.alignment = styles["center"]
                if cell.value is not None and cell.number_format == "General":
                    cell.number_format = "#,##0.0;(#,##0.0);-"

    def section(ws, row: int, title: str) -> None:
        ws.cell(row=row, column=1, value=title)
        for col in range(1, last_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = styles["section"]
            cell.font = styles["white"]

    def label(ws, row: int, text: str, source_type: str = "") -> None:
        ws.cell(row=row, column=1, value=text).font = styles["normal"]
        ws.cell(row=row, column=2, value=source_type).font = styles["normal"]

    def input_cell(cell, value: Any, source: str = "") -> None:
        cell.value = value
        cell.font = styles["input_font"]
        cell.fill = styles["input"]
        cell.alignment = styles["center"]
        if source:
            cell.comment = Comment(f"Source: {source}", "single-stock-coverage")

    def formula_cell(cell, formula: str, link: bool = False) -> None:
        cell.value = formula
        cell.font = styles["link"] if link else styles["formula"]
        cell.alignment = styles["center"]

    def pct_row(ws, row: int) -> None:
        for col in range(first_col, last_col + 1):
            ws.cell(row=row, column=col).number_format = "0.0%"

    for ws in sheets.values():
        set_title(ws, ws.title)
        set_period_headers(ws)

    cover = sheets["Cover"]
    for row, key, value in (
        (6, "Company", metadata["company"]),
        (7, "Ticker", metadata["ticker"]),
        (8, "Market", metadata["market"]),
        (9, "Fiscal Year End", metadata["fiscal_year_end"]),
        (10, "Model Date", datetime.now().strftime("%Y-%m-%d")),
        (12, "Artifact", "02_financial_model/integrated_model.xlsx"),
    ):
        cover.cell(row=row, column=1, value=key)
        cover.cell(row=row, column=2, value=value)

    sources = sheets["Sources"]
    for col, header in enumerate(("Source ID", "Period", "Source", "Notes"), start=1):
        sources.cell(row=6, column=col, value=header).fill = styles["header"]
        sources.cell(row=6, column=col).font = styles["bold"]
    unsourced_items = list(merged.get("unsourced") or [])
    for row, record in enumerate(historicals, start=7):
        source = _source_for(record)
        sources.cell(row=row, column=1, value=f"SRC-{row - 6:03d}")
        sources.cell(row=row, column=2, value=record["period"])
        sources.cell(row=row, column=3, value=source)
        sources.cell(row=row, column=4, value="Historical financial record")
        if source == "[UNSOURCED]":
            unsourced_items.append(f"{record['period']}: missing source")

    assumptions_ws = sheets["Assumptions"]
    assumptions_ws["A6"] = "Scenario"
    input_cell(assumptions_ws["B6"], "Base", "Task 2 assumption set")
    assumption_rows = {
        "Revenue Drivers": (9, {"Revenue Growth": (10, assumptions["revenue_growth"], "0.0%")}),
        "Margin Drivers": (
            13,
            {
                "Gross Margin": (14, assumptions["gross_margin"], "0.0%"),
                "Operating Expenses % Revenue": (
                    15,
                    assumptions["opex_pct_revenue"],
                    "0.0%",
                ),
                "Tax Rate": (16, assumptions["tax_rate"], "0.0%"),
            },
        ),
        "Working Capital Drivers": (
            19,
            {
                "AR Days": (20, assumptions["ar_days"], "0.0"),
                "Inventory % Revenue": (
                    21,
                    assumptions["inventory_pct_revenue"],
                    "0.0%",
                ),
                "AP Days": (22, assumptions["ap_days"], "0.0"),
            },
        ),
        "CapEx/D&A Drivers": (
            25,
            {
                "D&A % Revenue": (26, assumptions["da_pct_revenue"], "0.0%"),
                "CapEx % Revenue": (27, assumptions["capex_pct_revenue"], "0.0%"),
            },
        ),
        "Debt/Interest Drivers": (
            30,
            {
                "Interest Rate": (31, assumptions["interest_rate"], "0.0%"),
                "Debt Repayment % Beginning Debt": (
                    32,
                    assumptions["debt_repayment_pct"],
                    "0.0%",
                ),
            },
        ),
        "Share Count Drivers": (
            35,
            {
                "Diluted Shares Growth": (
                    36,
                    assumptions["diluted_shares_growth"],
                    "0.0%",
                ),
                "Dividend Payout % Net Income": (
                    37,
                    assumptions["dividend_payout_pct"],
                    "0.0%",
                ),
            },
        ),
    }
    for title, (header_row, rows) in assumption_rows.items():
        section(assumptions_ws, header_row, title)
        for name, (row, value, number_format) in rows.items():
            label(assumptions_ws, row, name, "Input")
            for col in range(first_col + actual_count, last_col + 1):
                cell = assumptions_ws.cell(row=row, column=col)
                input_cell(cell, value, "Task 2 child specs")
                cell.number_format = number_format

    revenue_build = sheets["Revenue Build"]
    section(revenue_build, 7, "Revenue Build")
    label(revenue_build, 10, "Core Revenue", "Input / Formula")
    label(revenue_build, 12, "Total Revenue", "Formula")
    label(revenue_build, 13, "YoY Growth", "Formula")
    pct_row(revenue_build, 13)
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        prev_col = _column_letter(idx - 1) if idx > first_col else ""
        if period["is_actual"]:
            input_cell(
                revenue_build.cell(row=10, column=idx),
                _historical_value(period["record"], "revenue"),
                _source_for(period["record"]),
            )
        else:
            formula_cell(
                revenue_build.cell(row=10, column=idx),
                f"={prev_col}12*(1+{_sheet_ref('Assumptions', f'{col}10')})",
            )
        formula_cell(revenue_build.cell(row=12, column=idx), f"={col}10")
        formula_cell(
            revenue_build.cell(row=13, column=idx),
            "=0" if idx == first_col else f"=IF({prev_col}12=0,0,{col}12/{prev_col}12-1)",
        )

    wc = sheets["Working Capital"]
    section(wc, 7, "Working Capital")
    for row, text in (
        (8, "Accounts Receivable"),
        (9, "Inventory"),
        (10, "Accounts Payable"),
        (11, "Net Working Capital"),
        (12, "Change in NWC"),
    ):
        label(wc, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if period["is_actual"]:
            record = period["record"]
            revenue = _historical_value(record, "revenue")
            values = (
                (8, _historical_value(record, "ar") or revenue * assumptions["ar_days"] / 365),
                (9, _historical_value(record, "inventory") or revenue * assumptions["inventory_pct_revenue"]),
                (10, _historical_value(record, "ap") or revenue * assumptions["ap_days"] / 365),
            )
            for row, value in values:
                input_cell(wc.cell(row=row, column=idx), value, _source_for(record))
        else:
            formula_cell(
                wc.cell(row=8, column=idx),
                f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}20')}/365",
                True,
            )
            formula_cell(
                wc.cell(row=9, column=idx),
                f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}21')}",
                True,
            )
            formula_cell(
                wc.cell(row=10, column=idx),
                f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}22')}/365",
                True,
            )
        formula_cell(wc.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")
        prev_col = _column_letter(idx - 1) if idx > first_col else ""
        formula_cell(
            wc.cell(row=12, column=idx),
            "=0" if idx == first_col else f"={col}11-{prev_col}11",
        )

    ppe = sheets["PP&E & D&A"]
    section(ppe, 7, "PP&E & D&A")
    for row, text in (
        (8, "Beginning PP&E"),
        (9, "CapEx"),
        (10, "D&A"),
        (11, "Ending PP&E"),
    ):
        label(ppe, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if idx == first_col:
            input_cell(
                ppe.cell(row=8, column=idx),
                _historical_value(period["record"], "ppe"),
                _source_for(period["record"]),
            )
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(ppe.cell(row=8, column=idx), f"={prev_col}11")
        if period["is_actual"]:
            record = period["record"]
            input_cell(
                ppe.cell(row=9, column=idx),
                abs(_historical_value(record, "capex")),
                _source_for(record),
            )
            input_cell(
                ppe.cell(row=10, column=idx),
                _historical_value(record, "da"),
                _source_for(record),
            )
        else:
            formula_cell(
                ppe.cell(row=9, column=idx),
                f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}27')}",
                True,
            )
            formula_cell(
                ppe.cell(row=10, column=idx),
                f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}26')}",
                True,
            )
        formula_cell(ppe.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")

    debt = sheets["Debt & Interest"]
    section(debt, 7, "Debt & Interest")
    for row, text in (
        (8, "Beginning Debt"),
        (9, "Debt Issuance"),
        (10, "Debt Repayment"),
        (11, "Ending Debt"),
        (12, "Interest Expense"),
    ):
        label(debt, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if idx == first_col:
            input_cell(
                debt.cell(row=8, column=idx),
                _historical_value(period["record"], "debt"),
                _source_for(period["record"]),
            )
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(debt.cell(row=8, column=idx), f"={prev_col}11")
        if period["is_actual"]:
            input_cell(debt.cell(row=9, column=idx), 0, _source_for(period["record"]))
            input_cell(debt.cell(row=10, column=idx), 0, _source_for(period["record"]))
            input_cell(
                debt.cell(row=12, column=idx),
                _historical_value(period["record"], "interest_expense"),
                _source_for(period["record"]),
            )
        else:
            formula_cell(debt.cell(row=9, column=idx), "=0")
            formula_cell(
                debt.cell(row=10, column=idx),
                f"={col}8*{_sheet_ref('Assumptions', f'{col}32')}",
            )
            formula_cell(
                debt.cell(row=12, column=idx),
                f"=(({col}8+{col}11)/2)*{_sheet_ref('Assumptions', f'{col}31')}",
            )
        formula_cell(debt.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")

    share = sheets["Share Count"]
    section(share, 7, "Share Count")
    for row, text in (
        (8, "Beginning Diluted Shares"),
        (9, "Share Issuance"),
        (10, "Buybacks"),
        (11, "Ending Diluted Shares"),
        (12, "Dividends"),
    ):
        label(share, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if idx == first_col:
            input_cell(
                share.cell(row=8, column=idx),
                _historical_value(period["record"], "shares"),
                _source_for(period["record"]),
            )
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(share.cell(row=8, column=idx), f"={prev_col}11")
        if period["is_actual"]:
            input_cell(share.cell(row=9, column=idx), 0, _source_for(period["record"]))
            input_cell(share.cell(row=10, column=idx), 0, _source_for(period["record"]))
            input_cell(
                share.cell(row=12, column=idx),
                _as_float(_field(period["record"], "dividends"), 0),
                _source_for(period["record"]),
            )
            formula_cell(share.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")
        else:
            formula_cell(share.cell(row=9, column=idx), "=0")
            formula_cell(share.cell(row=10, column=idx), "=0")
            formula_cell(
                share.cell(row=11, column=idx),
                f"={col}8*(1+{_sheet_ref('Assumptions', f'{col}36')})",
            )
            formula_cell(
                share.cell(row=12, column=idx),
                f"=MAX(0,{_sheet_ref('Income Statement', f'{col}20')}*{_sheet_ref('Assumptions', f'{col}37')})",
                True,
            )

    income = sheets["Income Statement"]
    section(income, 7, "Income Statement")
    for row, text in (
        (8, "Revenue"),
        (9, "COGS"),
        (10, "Gross Profit"),
        (12, "Operating Expenses"),
        (13, "D&A"),
        (14, "EBIT"),
        (15, "EBITDA"),
        (17, "Interest Expense"),
        (18, "Pretax Income"),
        (19, "Tax Expense"),
        (20, "Net Income"),
        (22, "Diluted Shares"),
        (23, "EPS Diluted"),
    ):
        label(income, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if period["is_actual"]:
            record = period["record"]
            revenue = _historical_value(record, "revenue")
            gross_profit = (
                _historical_value(record, "gross_profit")
                or revenue * assumptions["gross_margin"]
            )
            da = _historical_value(record, "da")
            ebit = (
                _historical_value(record, "ebit")
                or gross_profit - _historical_value(record, "operating_expenses") - da
            )
            interest = _historical_value(record, "interest_expense")
            pretax = _historical_value(record, "pretax_income") or ebit - interest
            tax = _historical_value(record, "tax_expense")
            net_income = _historical_value(record, "net_income") or pretax - tax
            values = {
                8: revenue,
                9: max(revenue - gross_profit, 0),
                10: gross_profit,
                12: max(gross_profit - ebit - da, 0),
                13: da,
                14: ebit,
                15: _historical_value(record, "ebitda") or ebit + da,
                17: interest,
                18: pretax,
                19: tax,
                20: net_income,
            }
            for row, value in values.items():
                input_cell(income.cell(row=row, column=idx), value, _source_for(record))
        else:
            formula_cell(
                income.cell(row=8, column=idx),
                f"={_sheet_ref('Revenue Build', f'{col}12')}",
                True,
            )
            formula_cell(
                income.cell(row=9, column=idx),
                f"={col}8*(1-{_sheet_ref('Assumptions', f'{col}14')})",
            )
            formula_cell(income.cell(row=10, column=idx), f"={col}8-{col}9")
            formula_cell(
                income.cell(row=12, column=idx),
                f"={col}8*{_sheet_ref('Assumptions', f'{col}15')}",
            )
            formula_cell(
                income.cell(row=13, column=idx),
                f"={_sheet_ref('PP&E & D&A', f'{col}10')}",
                True,
            )
            formula_cell(income.cell(row=14, column=idx), f"={col}10-{col}12-{col}13")
            formula_cell(income.cell(row=15, column=idx), f"={col}14+{col}13")
            formula_cell(
                income.cell(row=17, column=idx),
                f"={_sheet_ref('Debt & Interest', f'{col}12')}",
                True,
            )
            formula_cell(income.cell(row=18, column=idx), f"={col}14-{col}17")
            formula_cell(
                income.cell(row=19, column=idx),
                f"=MAX(0,{col}18*{_sheet_ref('Assumptions', f'{col}16')})",
            )
            formula_cell(income.cell(row=20, column=idx), f"={col}18-{col}19")
        formula_cell(
            income.cell(row=22, column=idx),
            f"={_sheet_ref('Share Count', f'{col}11')}",
            True,
        )
        formula_cell(income.cell(row=23, column=idx), f"=IF({col}22=0,0,{col}20/{col}22)")

    bs = sheets["Balance Sheet"]
    section(bs, 7, "Assets")
    section(bs, 17, "Liabilities")
    section(bs, 23, "Equity")
    for row, text in (
        (8, "Cash and Equivalents"),
        (9, "Accounts Receivable"),
        (10, "Inventory"),
        (11, "Total Current Assets"),
        (13, "PP&E Net"),
        (14, "Other Assets"),
        (15, "Total Assets"),
        (18, "Accounts Payable"),
        (19, "Total Current Liabilities"),
        (20, "Total Debt"),
        (21, "Total Liabilities"),
        (24, "Common Stock + APIC"),
        (25, "Retained Earnings"),
        (26, "Total Equity"),
        (27, "Total Liabilities and Equity"),
    ):
        label(bs, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if period["is_actual"]:
            input_cell(
                bs.cell(row=8, column=idx),
                _historical_value(period["record"], "cash"),
                _source_for(period["record"]),
            )
        else:
            formula_cell(
                bs.cell(row=8, column=idx),
                f"={_sheet_ref('Cash Flow Statement', f'{col}25')}",
                True,
            )
        formula_cell(bs.cell(row=9, column=idx), f"={_sheet_ref('Working Capital', f'{col}8')}", True)
        formula_cell(bs.cell(row=10, column=idx), f"={_sheet_ref('Working Capital', f'{col}9')}", True)
        formula_cell(bs.cell(row=11, column=idx), f"=SUM({col}8:{col}10)")
        formula_cell(bs.cell(row=13, column=idx), f"={_sheet_ref('PP&E & D&A', f'{col}11')}", True)
        formula_cell(bs.cell(row=14, column=idx), "=0")
        formula_cell(bs.cell(row=15, column=idx), f"={col}11+{col}13+{col}14")
        formula_cell(bs.cell(row=18, column=idx), f"={_sheet_ref('Working Capital', f'{col}10')}", True)
        formula_cell(bs.cell(row=19, column=idx), f"={col}18")
        formula_cell(bs.cell(row=20, column=idx), f"={_sheet_ref('Debt & Interest', f'{col}11')}", True)
        formula_cell(bs.cell(row=21, column=idx), f"={col}19+{col}20")
        if idx == first_col:
            input_cell(
                bs.cell(row=25, column=idx),
                _historical_value(period["record"], "retained_earnings"),
                _source_for(period["record"]),
            )
        elif period["is_actual"]:
            input_cell(
                bs.cell(row=25, column=idx),
                _historical_value(period["record"], "retained_earnings"),
                _source_for(period["record"]),
            )
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(
                bs.cell(row=25, column=idx),
                f"={prev_col}25+{_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Share Count', f'{col}12')}",
                True,
            )
        formula_cell(bs.cell(row=24, column=idx), f"={col}15-{col}21-{col}25")
        formula_cell(bs.cell(row=26, column=idx), f"={col}24+{col}25")
        formula_cell(bs.cell(row=27, column=idx), f"={col}21+{col}26")

    cf = sheets["Cash Flow Statement"]
    section(cf, 7, "Operating Activities")
    section(cf, 13, "Investing Activities")
    section(cf, 17, "Financing Activities")
    for row, text in (
        (8, "Net Income"),
        (9, "D&A Addback"),
        (10, "Change in NWC"),
        (11, "CFO Total"),
        (14, "CapEx"),
        (15, "CFI Total"),
        (18, "Debt Issuance"),
        (19, "Debt Repayment"),
        (20, "Dividends"),
        (21, "CFF Total"),
        (23, "Net Change in Cash"),
        (24, "Beginning Cash"),
        (25, "Ending Cash"),
    ):
        label(cf, row, text, "Formula")
    for idx, _period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        formula_cell(cf.cell(row=8, column=idx), f"={_sheet_ref('Income Statement', f'{col}20')}", True)
        formula_cell(cf.cell(row=9, column=idx), f"={_sheet_ref('PP&E & D&A', f'{col}10')}", True)
        formula_cell(cf.cell(row=10, column=idx), f"=-{_sheet_ref('Working Capital', f'{col}12')}", True)
        formula_cell(cf.cell(row=11, column=idx), f"=SUM({col}8:{col}10)")
        formula_cell(cf.cell(row=14, column=idx), f"=-{_sheet_ref('PP&E & D&A', f'{col}9')}", True)
        formula_cell(cf.cell(row=15, column=idx), f"={col}14")
        formula_cell(cf.cell(row=18, column=idx), f"={_sheet_ref('Debt & Interest', f'{col}9')}", True)
        formula_cell(cf.cell(row=19, column=idx), f"=-{_sheet_ref('Debt & Interest', f'{col}10')}", True)
        formula_cell(cf.cell(row=20, column=idx), f"=-{_sheet_ref('Share Count', f'{col}12')}", True)
        formula_cell(cf.cell(row=21, column=idx), f"=SUM({col}18:{col}20)")
        formula_cell(cf.cell(row=23, column=idx), f"={col}11+{col}15+{col}21")
        if idx == first_col:
            formula_cell(
                cf.cell(row=24, column=idx),
                f"={_sheet_ref('Balance Sheet', f'{col}8')}-{col}23",
                True,
            )
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(cf.cell(row=24, column=idx), f"={prev_col}25")
        formula_cell(cf.cell(row=25, column=idx), f"={col}24+{col}23")

    dcf = sheets["DCF Inputs"]
    section(dcf, 7, "DCF Inputs")
    for row, text in (
        (8, "Revenue"),
        (9, "EBIT"),
        (10, "Tax Rate"),
        (11, "D&A"),
        (12, "CapEx"),
        (13, "Change in NWC"),
        (14, "Total Debt"),
        (15, "Cash"),
        (16, "Diluted Shares"),
        (17, "Scenario Label"),
    ):
        label(dcf, row, text, "Formula")
    for idx in range(first_col, last_col + 1):
        col = _column_letter(idx)
        refs = {
            8: _sheet_ref("Income Statement", f"{col}8"),
            9: _sheet_ref("Income Statement", f"{col}14"),
            10: _sheet_ref("Assumptions", f"{col}16"),
            11: _sheet_ref("Income Statement", f"{col}13"),
            12: _sheet_ref("Cash Flow Statement", f"{col}14"),
            13: _sheet_ref("Cash Flow Statement", f"{col}10"),
            14: _sheet_ref("Balance Sheet", f"{col}20"),
            15: _sheet_ref("Balance Sheet", f"{col}8"),
            16: _sheet_ref("Share Count", f"{col}11"),
            17: _sheet_ref("Assumptions", "$B$6"),
        }
        for row, ref in refs.items():
            formula_cell(dcf.cell(row=row, column=idx), f"={ref}", True)

    checks = sheets["Checks"]
    checks["A4"] = "Failing Check Count"
    formula_cell(checks["B4"], f"=COUNTIF(C8:{_column_letter(last_col)}15,\"<>0\")")
    for row, text in (
        (8, "BS Balance"),
        (9, "Cash Tie-Out"),
        (10, "NI Link"),
        (11, "RE Roll-Forward"),
        (12, "CapEx/PP&E Tie"),
        (13, "Debt Tie"),
        (14, "Revenue Tie"),
        (15, "D&A Tie"),
    ):
        label(checks, row, text, "Formula")
    for idx in range(first_col, last_col + 1):
        col = _column_letter(idx)
        prev_col = _column_letter(idx - 1) if idx > first_col else ""
        formulas = {
            8: f"={_sheet_ref('Balance Sheet', f'{col}15')}-{_sheet_ref('Balance Sheet', f'{col}27')}",
            9: f"={_sheet_ref('Cash Flow Statement', f'{col}25')}-{_sheet_ref('Balance Sheet', f'{col}8')}",
            10: f"={_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Cash Flow Statement', f'{col}8')}",
            11: "=0" if idx == first_col else f"={_sheet_ref('Balance Sheet', f'{prev_col}25')}+{_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Share Count', f'{col}12')}-{_sheet_ref('Balance Sheet', f'{col}25')}",
            12: f"={_sheet_ref('PP&E & D&A', f'{col}11')}-{_sheet_ref('PP&E & D&A', f'{col}8')}-{_sheet_ref('PP&E & D&A', f'{col}9')}+{_sheet_ref('PP&E & D&A', f'{col}10')}",
            13: f"={_sheet_ref('Debt & Interest', f'{col}11')}-{_sheet_ref('Debt & Interest', f'{col}8')}-{_sheet_ref('Debt & Interest', f'{col}9')}+{_sheet_ref('Debt & Interest', f'{col}10')}",
            14: f"={_sheet_ref('Income Statement', f'{col}8')}-{_sheet_ref('Revenue Build', f'{col}12')}",
            15: f"={_sheet_ref('Income Statement', f'{col}13')}-{_sheet_ref('PP&E & D&A', f'{col}10')}",
        }
        for row, formula in formulas.items():
            formula_cell(checks.cell(row=row, column=idx), formula)

    for name, ref in {
        "ScenarioSelector": "'Assumptions'!$B$6",
        "RevDriverBlock": f"'Assumptions'!$C$10:${_column_letter(last_col)}$10",
        "MarginDriverBlock": f"'Assumptions'!$C$14:${_column_letter(last_col)}$16",
        "NWCDriverBlock": f"'Assumptions'!$C$20:${_column_letter(last_col)}$22",
        "CapExDriverBlock": f"'Assumptions'!$C$26:${_column_letter(last_col)}$27",
        "DebtDriverBlock": f"'Assumptions'!$C$31:${_column_letter(last_col)}$32",
    }.items():
        wb.defined_names.add(DefinedName(name, attr_text=ref))

    for ws in sheets.values():
        format_sheet(ws)

    if hasattr(wb, "calculation"):
        wb.calculation.fullCalcOnLoad = True
        wb.calculation.forceFullCalc = True
    wb.save(workbook_path)

    return _json_result(
        {
            "status": "OK",
            "workbook_path": _relative_to_workspace(workbook_path),
            "row_map": row_map,
            "period_columns": period_columns,
            "warnings": [],
            "unsourced_items": sorted(set(str(item) for item in unsourced_items)),
        }
    )


def _scoped_validate_integrated_three_statement_model_reference(
    excel_path: str,
    row_map_json: str = "",
) -> str:
    """Validate deterministic Task 2 integrated_model.xlsx structure and formulas."""
    try:
        import openpyxl
    except ImportError as exc:
        return _json_result(
            {"status": "ERROR", "message": f"openpyxl is not installed: {exc}"}
        )

    path = _resolve_workspace_path(excel_path)
    if not path.exists():
        return _validation_result(
            "FAIL",
            [
                {
                    "sheet": "",
                    "cell": "",
                    "category": "Missing File",
                    "issue": f"Workbook not found: {path}",
                }
            ],
            [],
        )

    row_map = DEFAULT_THREE_STATEMENT_ROW_MAP
    if row_map_json:
        parsed = _json_loads(row_map_json, "row_map_json")
        if (
            isinstance(parsed, dict)
            and isinstance(parsed.get("row_map"), dict)
        ):
            row_map = parsed["row_map"]
        elif isinstance(parsed, dict):
            row_map = parsed

    wb = openpyxl.load_workbook(path, data_only=False)
    critical: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for sheet_name in THREE_STATEMENT_TABS:
        if sheet_name not in wb.sheetnames:
            critical.append(
                {
                    "sheet": sheet_name,
                    "cell": "",
                    "category": "Missing Required Tab",
                    "issue": f"Required tab '{sheet_name}' is absent.",
                }
            )
    if critical:
        return _validation_result("FAIL", critical, warnings)

    defined_names = set(wb.defined_names)
    for name in REQUIRED_MODEL_NAMES:
        if name not in defined_names:
            critical.append(
                {
                    "sheet": "Assumptions",
                    "cell": name,
                    "category": "Missing Named Range",
                    "issue": f"Named range '{name}' is required for Task 2 handoff.",
                }
            )

    checks = wb["Checks"]
    forecast_cols = [
        col
        for col in range(3, checks.max_column + 1)
        if str(checks.cell(row=4, column=col).value or "").lower() == "forecast"
    ]
    if not forecast_cols:
        warnings.append(
            {
                "sheet": "Checks",
                "cell": "4:4",
                "category": "Period Metadata",
                "issue": "No forecast columns were marked in row 4; validating all modeled period columns.",
            }
        )
        forecast_cols = list(range(3, checks.max_column + 1))

    formula_requirements: list[tuple[str, list[int]]] = [
        (
            "Revenue Build",
            [
                row_map["revenue_build"]["core_revenue"],
                row_map["revenue_build"]["revenue_total"],
                row_map["revenue_build"]["revenue_growth"],
            ],
        ),
        ("Income Statement", list(row_map["income_statement"].values())),
        ("Balance Sheet", list(row_map["balance_sheet"].values())),
        ("Cash Flow Statement", list(row_map["cash_flow"].values())),
        ("Working Capital", list(row_map["working_capital"].values())),
        ("PP&E & D&A", list(row_map["ppe_da"].values())),
        ("Debt & Interest", list(row_map["debt_interest"].values())),
        ("Share Count", list(row_map["share_count"].values())),
        ("DCF Inputs", list(row_map["dcf_inputs"].values())),
        (
            "Checks",
            [
                row
                for key, row in row_map["checks"].items()
                if key != "failing_check_count"
            ],
        ),
    ]
    for sheet_name, rows in formula_requirements:
        ws = wb[sheet_name]
        for row in sorted(set(rows)):
            for col in forecast_cols:
                value = ws.cell(row=row, column=col).value
                if not _formula(value):
                    critical.append(
                        {
                            "sheet": sheet_name,
                            "cell": f"{_column_letter(col)}{row}",
                            "category": "Projection Hardcode",
                            "issue": "Forecast/model cell must be an Excel formula.",
                        }
                    )

    bs = wb["Balance Sheet"]
    cf = wb["Cash Flow Statement"]
    for col in forecast_cols:
        col_letter = _column_letter(col)
        bs_cash_row = row_map["balance_sheet"]["cash_and_equivalents"]
        cf_cash_row = row_map["cash_flow"]["ending_cash"]
        bs_cash = bs.cell(row=bs_cash_row, column=col).value
        cf_cash = cf.cell(row=cf_cash_row, column=col).value
        if not (
            _formula(bs_cash)
            and "Cash Flow Statement" in bs_cash
            and f"{col_letter}{cf_cash_row}" in bs_cash
        ):
            critical.append(
                {
                    "sheet": "Balance Sheet",
                    "cell": f"{col_letter}{bs_cash_row}",
                    "category": "Cash Tie-Out",
                    "issue": "Forecast BS cash must link to Cash Flow Statement ending cash.",
                }
            )
        if not _formula(cf_cash):
            critical.append(
                {
                    "sheet": "Cash Flow Statement",
                    "cell": f"{col_letter}{cf_cash_row}",
                    "category": "Cash Tie-Out",
                    "issue": "Forecast CF ending cash must be formula-driven.",
                }
            )

    dcf = wb["DCF Inputs"]
    for row in row_map["dcf_inputs"].values():
        for col in forecast_cols:
            value = dcf.cell(row=row, column=col).value
            if not _formula(value):
                critical.append(
                    {
                        "sheet": "DCF Inputs",
                        "cell": f"{_column_letter(col)}{row}",
                        "category": "DCF Input Hardcode",
                        "issue": "DCF Inputs must pull from linked model cells.",
                    }
                )

    return _validation_result("PASS" if not critical else "FAIL", critical, warnings)


@tool
def update_run_manifest(
    patch_json: str,
    ticker: str,
    market: str,
    run_dir: str = "",
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
def build_integrated_three_statement_model(
    model_input_json: str,
    run_dir: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Build deterministic Task 2 integrated_model.xlsx from statement specs."""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.workbook.defined_name import DefinedName
    except ImportError as exc:
        return _json_result({"status": "ERROR", "message": f"openpyxl is not installed: {exc}"})

    payload = _json_loads(model_input_json, "model_input_json")
    if not isinstance(payload, dict):
        raise ValueError("model_input_json must be a JSON object")
    merged = _merge_payload_model_input(payload)
    historicals = _historical_records(merged)
    latest = historicals[-1]
    forecast_labels = _forecast_labels(merged, latest["year"])
    metadata = _model_metadata(merged)
    assumptions = _assumption_set(merged, latest)

    out_dir = _resolve_workspace_path(run_dir) if run_dir else _find_run_dir(
        market=metadata["market"] or "market",
        ticker=metadata["ticker"],
        output_dir=output_dir,
    )
    model_dir = _statement_model_dir(out_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = model_dir / "integrated_model.xlsx"

    periods: list[dict[str, Any]] = [
        {"label": record["period"], "record": record, "is_actual": True}
        for record in historicals
    ]
    periods.extend(
        {"label": label, "record": {}, "is_actual": False}
        for label in forecast_labels
    )
    first_col = 3
    last_col = first_col + len(periods) - 1
    actual_count = len(historicals)
    period_columns = {
        period["label"]: _column_letter(idx)
        for idx, period in enumerate(periods, start=first_col)
    }
    row_map = json.loads(json.dumps(DEFAULT_THREE_STATEMENT_ROW_MAP))
    unsourced_items = list(merged.get("unsourced") or [])

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheets = {name: wb.create_sheet(name) for name in THREE_STATEMENT_TABS}
    navy_fill = PatternFill("solid", fgColor="1F4E79")
    blue_fill = PatternFill("solid", fgColor="D9E1F2")
    input_font = Font(name="Arial", color="0000FF")
    formula_font = Font(name="Arial", color="000000")
    link_font = Font(name="Arial", color="008000")
    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    bold_font = Font(name="Arial", bold=True, color="000000")
    center = Alignment(horizontal="center", vertical="center")

    def init_sheet(ws, title: str) -> None:
        ws["A1"] = title
        ws["A1"].fill = navy_fill
        ws["A1"].font = header_font
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(last_col, 6))
        ws["A3"] = f"Currency: {metadata['currency']} | Unit: {metadata['unit']}"
        ws["A5"] = "Line Item"
        ws["B5"] = "Source / Type"
        for cell in (ws["A5"], ws["B5"]):
            cell.fill = blue_fill
            cell.font = bold_font
        for col_idx, period in enumerate(periods, start=first_col):
            col = _column_letter(col_idx)
            ws.cell(row=4, column=col_idx, value="Actual" if period["is_actual"] else "Forecast")
            ws.cell(row=5, column=col_idx, value=period["label"])
            ws[f"{col}4"].font = bold_font
            ws[f"{col}5"].font = bold_font
            ws[f"{col}5"].fill = blue_fill
        ws.freeze_panes = "C6"
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 18
        for col_idx in range(first_col, last_col + 1):
            ws.column_dimensions[_column_letter(col_idx)].width = 14

    def section(ws, row: int, title: str) -> None:
        ws.cell(row=row, column=1, value=title)
        for col_idx in range(1, last_col + 1):
            cell = ws.cell(row=row, column=col_idx)
            cell.fill = navy_fill
            cell.font = header_font

    def label(ws, row: int, text: str, source_type: str = "Formula") -> None:
        ws.cell(row=row, column=1, value=text)
        ws.cell(row=row, column=2, value=source_type)

    def input_cell(ws, row: int, col_idx: int, value: Any) -> None:
        cell = ws.cell(row=row, column=col_idx, value=value)
        cell.font = input_font
        cell.alignment = center

    def formula_cell(ws, row: int, col_idx: int, formula: str, link: bool = False) -> None:
        cell = ws.cell(row=row, column=col_idx, value=formula)
        cell.font = link_font if link else formula_font
        cell.alignment = center

    for ws in sheets.values():
        init_sheet(ws, ws.title)

    cover = sheets["Cover"]
    for row, label_text, value in (
        (6, "Company", metadata["company"]),
        (7, "Ticker", metadata["ticker"]),
        (8, "Market", metadata["market"]),
        (9, "Fiscal Year End", metadata["fiscal_year_end"]),
        (10, "Workbook", "02_financial_model/integrated_model.xlsx"),
    ):
        label(cover, row, label_text, "Metadata")
        cover.cell(row=row, column=2, value=value)

    sources = sheets["Sources"]
    for idx, record in enumerate(historicals, start=7):
        label(sources, idx, record["period"], "Source")
        source = _source_for(record)
        sources.cell(row=idx, column=3, value=source)
        if source == "[UNSOURCED]":
            unsourced_items.append(f"{record['period']}: missing source")

    assumptions_ws = sheets["Assumptions"]
    label(assumptions_ws, 6, "Scenario", "Input")
    assumptions_ws["B6"] = "Base"
    assumption_rows = {
        10: assumptions["revenue_growth"],
        14: assumptions["gross_margin"],
        15: assumptions["opex_pct_revenue"],
        16: assumptions["tax_rate"],
        20: assumptions["ar_days"],
        21: assumptions["inventory_pct_revenue"],
        22: assumptions["ap_days"],
        26: assumptions["da_pct_revenue"],
        27: assumptions["capex_pct_revenue"],
        31: assumptions["interest_rate"],
        32: assumptions["debt_repayment_pct"],
        36: assumptions["diluted_shares_growth"],
        37: assumptions["dividend_payout_pct"],
    }
    for header_row, title in (
        (9, "Revenue Drivers"),
        (13, "Margin Drivers"),
        (19, "Working Capital Drivers"),
        (25, "CapEx/D&A Drivers"),
        (30, "Debt/Interest Drivers"),
        (35, "Share Count Drivers"),
    ):
        section(assumptions_ws, header_row, title)
    for row, value in assumption_rows.items():
        label(assumptions_ws, row, f"Assumption {row}", "Input")
        for col_idx in range(first_col + actual_count, last_col + 1):
            input_cell(assumptions_ws, row, col_idx, value)

    revenue_build = sheets["Revenue Build"]
    section(revenue_build, 7, "Revenue Build")
    for row, text in ((10, "Core Revenue"), (12, "Total Revenue"), (13, "YoY Growth")):
        label(revenue_build, row, text)

    wc = sheets["Working Capital"]
    section(wc, 7, "Working Capital")
    for row, text in ((8, "Accounts Receivable"), (9, "Inventory"), (10, "Accounts Payable"), (11, "Net Working Capital"), (12, "Change in NWC")):
        label(wc, row, text)

    ppe = sheets["PP&E & D&A"]
    section(ppe, 7, "PP&E & D&A")
    for row, text in ((8, "Beginning PP&E"), (9, "CapEx"), (10, "D&A"), (11, "Ending PP&E")):
        label(ppe, row, text)

    debt = sheets["Debt & Interest"]
    section(debt, 7, "Debt & Interest")
    for row, text in ((8, "Beginning Debt"), (9, "Debt Issuance"), (10, "Debt Repayment"), (11, "Ending Debt"), (12, "Interest Expense")):
        label(debt, row, text)

    share = sheets["Share Count"]
    section(share, 7, "Share Count")
    for row, text in ((8, "Beginning Diluted Shares"), (9, "Share Issuance"), (10, "Buybacks"), (11, "Ending Diluted Shares"), (12, "Dividends")):
        label(share, row, text)

    income = sheets["Income Statement"]
    section(income, 7, "Income Statement")
    for row, text in ((8, "Revenue"), (9, "COGS"), (10, "Gross Profit"), (12, "Operating Expenses"), (13, "D&A"), (14, "EBIT"), (15, "EBITDA"), (17, "Interest Expense"), (18, "Pretax Income"), (19, "Tax Expense"), (20, "Net Income"), (22, "Diluted Shares"), (23, "EPS Diluted")):
        label(income, row, text)

    bs = sheets["Balance Sheet"]
    section(bs, 7, "Assets")
    section(bs, 17, "Liabilities")
    section(bs, 23, "Equity")
    for row, text in ((8, "Cash and Equivalents"), (9, "Accounts Receivable"), (10, "Inventory"), (11, "Total Current Assets"), (13, "PP&E Net"), (14, "Other Assets"), (15, "Total Assets"), (18, "Accounts Payable"), (19, "Total Current Liabilities"), (20, "Total Debt"), (21, "Total Liabilities"), (24, "Common Stock + APIC"), (25, "Retained Earnings"), (26, "Total Equity"), (27, "Total Liabilities and Equity")):
        label(bs, row, text)

    cf = sheets["Cash Flow Statement"]
    section(cf, 7, "Operating Activities")
    section(cf, 13, "Investing Activities")
    section(cf, 17, "Financing Activities")
    for row, text in ((8, "Net Income"), (9, "D&A Addback"), (10, "Change in NWC"), (11, "CFO Total"), (14, "CapEx"), (15, "CFI Total"), (18, "Debt Issuance"), (19, "Debt Repayment"), (20, "Dividends"), (21, "CFF Total"), (23, "Net Change in Cash"), (24, "Beginning Cash"), (25, "Ending Cash")):
        label(cf, row, text)

    dcf = sheets["DCF Inputs"]
    section(dcf, 7, "DCF Inputs")
    for row, text in ((8, "Revenue"), (9, "EBIT"), (10, "Tax Rate"), (11, "D&A"), (12, "CapEx"), (13, "Change in NWC"), (14, "Total Debt"), (15, "Cash"), (16, "Diluted Shares"), (17, "Scenario Label")):
        label(dcf, row, text)

    checks = sheets["Checks"]
    label(checks, 4, "Failing Check Count", "Formula")
    for row, text in ((8, "BS Balance"), (9, "Cash Tie-Out"), (10, "NI Link"), (11, "RE Roll-Forward"), (12, "CapEx/PP&E Tie"), (13, "Debt Tie"), (14, "Revenue Tie"), (15, "D&A Tie")):
        label(checks, row, text)

    for col_idx, period in enumerate(periods, start=first_col):
        col = _column_letter(col_idx)
        prev_col = _column_letter(col_idx - 1) if col_idx > first_col else ""
        is_actual = bool(period["is_actual"])
        record = period["record"]

        if is_actual:
            revenue = _historical_value(record, "revenue")
            gross_profit = _historical_value(record, "gross_profit") or revenue * assumptions["gross_margin"]
            ebit = _historical_value(record, "ebit") or gross_profit - _historical_value(record, "operating_expenses") - _historical_value(record, "da")
            pretax = _historical_value(record, "pretax_income") or ebit - _historical_value(record, "interest_expense")
            net_income = _historical_value(record, "net_income") or pretax - _historical_value(record, "tax_expense")
            for ws, row, value in (
                (revenue_build, 10, revenue),
                (income, 8, revenue),
                (income, 10, gross_profit),
                (income, 13, _historical_value(record, "da")),
                (income, 14, ebit),
                (income, 15, _historical_value(record, "ebitda") or ebit + _historical_value(record, "da")),
                (income, 17, _historical_value(record, "interest_expense")),
                (income, 18, pretax),
                (income, 19, _historical_value(record, "tax_expense")),
                (income, 20, net_income),
                (bs, 8, _historical_value(record, "cash")),
                (bs, 20, _historical_value(record, "debt")),
                (bs, 25, _historical_value(record, "retained_earnings")),
                (ppe, 8, _historical_value(record, "ppe")),
                (ppe, 9, abs(_historical_value(record, "capex"))),
                (ppe, 10, _historical_value(record, "da")),
                (debt, 8, _historical_value(record, "debt")),
                (debt, 12, _historical_value(record, "interest_expense")),
                (share, 8, _historical_value(record, "shares")),
            ):
                input_cell(ws, row, col_idx, value)
        else:
            formula_cell(revenue_build, 10, col_idx, f"={prev_col}12*(1+{_sheet_ref('Assumptions', f'{col}10')})")
            formula_cell(income, 8, col_idx, f"={_sheet_ref('Revenue Build', f'{col}12')}", True)
            formula_cell(income, 10, col_idx, f"={col}8*{_sheet_ref('Assumptions', f'{col}14')}")
            formula_cell(income, 13, col_idx, f"={_sheet_ref('PP&E & D&A', f'{col}10')}", True)
            formula_cell(income, 14, col_idx, f"={col}10-{col}12-{col}13")
            formula_cell(income, 15, col_idx, f"={col}14+{col}13")
            formula_cell(income, 17, col_idx, f"={_sheet_ref('Debt & Interest', f'{col}12')}", True)
            formula_cell(income, 18, col_idx, f"={col}14-{col}17")
            formula_cell(income, 19, col_idx, f"=MAX(0,{col}18*{_sheet_ref('Assumptions', f'{col}16')})")
            formula_cell(income, 20, col_idx, f"={col}18-{col}19")
            formula_cell(bs, 8, col_idx, f"={_sheet_ref('Cash Flow Statement', f'{col}25')}", True)
            formula_cell(bs, 25, col_idx, f"={prev_col}25+{_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Share Count', f'{col}12')}", True)
            formula_cell(ppe, 8, col_idx, f"={prev_col}11")
            formula_cell(ppe, 9, col_idx, f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}27')}", True)
            formula_cell(ppe, 10, col_idx, f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}26')}", True)
            formula_cell(debt, 8, col_idx, f"={prev_col}11")
            formula_cell(debt, 12, col_idx, f"=(({col}8+{col}11)/2)*{_sheet_ref('Assumptions', f'{col}31')}")
            formula_cell(share, 8, col_idx, f"={prev_col}11")

        formula_cell(revenue_build, 12, col_idx, f"={col}10")
        formula_cell(revenue_build, 13, col_idx, "=0" if col_idx == first_col else f"=IF({prev_col}12=0,0,{col}12/{prev_col}12-1)")
        formula_cell(income, 9, col_idx, f"={col}8-{col}10")
        formula_cell(income, 12, col_idx, f"={col}8*{_sheet_ref('Assumptions', f'{col}15')}" if not is_actual else f"=MAX(0,{col}10-{col}14-{col}13)")
        formula_cell(income, 22, col_idx, f"={_sheet_ref('Share Count', f'{col}11')}", True)
        formula_cell(income, 23, col_idx, f"=IF({col}22=0,0,{col}20/{col}22)")
        formula_cell(wc, 8, col_idx, f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}20')}/365", True)
        formula_cell(wc, 9, col_idx, f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}21')}", True)
        formula_cell(wc, 10, col_idx, f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}22')}/365", True)
        formula_cell(wc, 11, col_idx, f"={col}8+{col}9-{col}10")
        formula_cell(wc, 12, col_idx, "=0" if col_idx == first_col else f"={col}11-{prev_col}11")
        formula_cell(ppe, 11, col_idx, f"={col}8+{col}9-{col}10")
        formula_cell(debt, 9, col_idx, "=0")
        formula_cell(debt, 10, col_idx, f"={col}8*{_sheet_ref('Assumptions', f'{col}32')}" if not is_actual else "=0")
        formula_cell(debt, 11, col_idx, f"={col}8+{col}9-{col}10")
        formula_cell(share, 9, col_idx, "=0")
        formula_cell(share, 10, col_idx, "=0")
        formula_cell(share, 11, col_idx, f"={col}8*(1+{_sheet_ref('Assumptions', f'{col}36')})" if not is_actual else f"={col}8+{col}9-{col}10")
        formula_cell(share, 12, col_idx, f"=MAX(0,{_sheet_ref('Income Statement', f'{col}20')}*{_sheet_ref('Assumptions', f'{col}37')})", True)
        formula_cell(bs, 9, col_idx, f"={_sheet_ref('Working Capital', f'{col}8')}", True)
        formula_cell(bs, 10, col_idx, f"={_sheet_ref('Working Capital', f'{col}9')}", True)
        formula_cell(bs, 11, col_idx, f"=SUM({col}8:{col}10)")
        formula_cell(bs, 13, col_idx, f"={_sheet_ref('PP&E & D&A', f'{col}11')}", True)
        formula_cell(bs, 14, col_idx, "=0")
        formula_cell(bs, 15, col_idx, f"={col}11+{col}13+{col}14")
        formula_cell(bs, 18, col_idx, f"={_sheet_ref('Working Capital', f'{col}10')}", True)
        formula_cell(bs, 19, col_idx, f"={col}18")
        formula_cell(bs, 20, col_idx, f"={_sheet_ref('Debt & Interest', f'{col}11')}", True)
        formula_cell(bs, 21, col_idx, f"={col}19+{col}20")
        formula_cell(bs, 24, col_idx, f"={col}15-{col}21-{col}25")
        formula_cell(bs, 26, col_idx, f"={col}24+{col}25")
        formula_cell(bs, 27, col_idx, f"={col}21+{col}26")
        formula_cell(cf, 8, col_idx, f"={_sheet_ref('Income Statement', f'{col}20')}", True)
        formula_cell(cf, 9, col_idx, f"={_sheet_ref('PP&E & D&A', f'{col}10')}", True)
        formula_cell(cf, 10, col_idx, f"=-{_sheet_ref('Working Capital', f'{col}12')}", True)
        formula_cell(cf, 11, col_idx, f"=SUM({col}8:{col}10)")
        formula_cell(cf, 14, col_idx, f"=-{_sheet_ref('PP&E & D&A', f'{col}9')}", True)
        formula_cell(cf, 15, col_idx, f"={col}14")
        formula_cell(cf, 18, col_idx, f"={_sheet_ref('Debt & Interest', f'{col}9')}", True)
        formula_cell(cf, 19, col_idx, f"=-{_sheet_ref('Debt & Interest', f'{col}10')}", True)
        formula_cell(cf, 20, col_idx, f"=-{_sheet_ref('Share Count', f'{col}12')}", True)
        formula_cell(cf, 21, col_idx, f"=SUM({col}18:{col}20)")
        formula_cell(cf, 23, col_idx, f"={col}11+{col}15+{col}21")
        formula_cell(cf, 24, col_idx, f"={_sheet_ref('Balance Sheet', f'{col}8')}-{col}23" if col_idx == first_col else f"={prev_col}25", True)
        formula_cell(cf, 25, col_idx, f"={col}24+{col}23")
        for row, ref in {
            8: _sheet_ref("Income Statement", f"{col}8"),
            9: _sheet_ref("Income Statement", f"{col}14"),
            10: _sheet_ref("Assumptions", f"{col}16"),
            11: _sheet_ref("Income Statement", f"{col}13"),
            12: _sheet_ref("Cash Flow Statement", f"{col}14"),
            13: _sheet_ref("Cash Flow Statement", f"{col}10"),
            14: _sheet_ref("Balance Sheet", f"{col}20"),
            15: _sheet_ref("Balance Sheet", f"{col}8"),
            16: _sheet_ref("Share Count", f"{col}11"),
            17: _sheet_ref("Assumptions", "$B$6"),
        }.items():
            formula_cell(dcf, row, col_idx, f"={ref}", True)
        formulas = {
            8: f"={_sheet_ref('Balance Sheet', f'{col}15')}-{_sheet_ref('Balance Sheet', f'{col}27')}",
            9: f"={_sheet_ref('Cash Flow Statement', f'{col}25')}-{_sheet_ref('Balance Sheet', f'{col}8')}",
            10: f"={_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Cash Flow Statement', f'{col}8')}",
            11: "=0" if col_idx == first_col else f"={_sheet_ref('Balance Sheet', f'{prev_col}25')}+{_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Share Count', f'{col}12')}-{_sheet_ref('Balance Sheet', f'{col}25')}",
            12: f"={_sheet_ref('PP&E & D&A', f'{col}11')}-{_sheet_ref('PP&E & D&A', f'{col}8')}-{_sheet_ref('PP&E & D&A', f'{col}9')}+{_sheet_ref('PP&E & D&A', f'{col}10')}",
            13: f"={_sheet_ref('Debt & Interest', f'{col}11')}-{_sheet_ref('Debt & Interest', f'{col}8')}-{_sheet_ref('Debt & Interest', f'{col}9')}+{_sheet_ref('Debt & Interest', f'{col}10')}",
            14: f"={_sheet_ref('Income Statement', f'{col}8')}-{_sheet_ref('Revenue Build', f'{col}12')}",
            15: f"={_sheet_ref('Income Statement', f'{col}13')}-{_sheet_ref('PP&E & D&A', f'{col}10')}",
        }
        for row, formula in formulas.items():
            formula_cell(checks, row, col_idx, formula)

    formula_cell(checks, 4, 2, f"=COUNTIF(C8:{_column_letter(last_col)}15,\"<>0\")")
    for name, ref in {
        "ScenarioSelector": "'Assumptions'!$B$6",
        "RevDriverBlock": f"'Assumptions'!$C$10:${_column_letter(last_col)}$10",
        "MarginDriverBlock": f"'Assumptions'!$C$14:${_column_letter(last_col)}$16",
        "NWCDriverBlock": f"'Assumptions'!$C$20:${_column_letter(last_col)}$22",
        "CapExDriverBlock": f"'Assumptions'!$C$26:${_column_letter(last_col)}$27",
        "DebtDriverBlock": f"'Assumptions'!$C$31:${_column_letter(last_col)}$32",
    }.items():
        wb.defined_names.add(DefinedName(name, attr_text=ref))

    for ws in sheets.values():
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cell.alignment = center
                    if cell.number_format == "General":
                        cell.number_format = "#,##0.0;(#,##0.0);-"

    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(workbook_path)
    return _json_result(
        {
            "status": "OK",
            "workbook_path": _relative_to_workspace(workbook_path),
            "row_map": row_map,
            "period_columns": period_columns,
            "warnings": [],
            "unsourced_items": sorted(set(str(item) for item in unsourced_items)),
        }
    )


@tool
def update_integrated_three_statement_model(
    prior_workbook_path: str,
    run_dir: str,
    model_input_json: str = "",
    statement_spec_pack_json: str = "",
    update_scope_json: str = "{}",
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Refresh an existing Task 2 workbook into the current run directory.

    The update executor uses this only after statement specs are reconciled. It
    does not fetch data; it copies the prior workbook, preserves formulas, marks
    the workbook for recalculation, and returns the current-run workbook path for
    validation/audit.
    """
    del output_dir
    source_path = _resolve_workspace_path(prior_workbook_path)
    if not source_path.exists():
        return _json_result(
            {
                "status": "FAIL",
                "workbook_path": "",
                "critical_count": 1,
                "critical": [
                    {
                        "category": "Missing Prior Workbook",
                        "issue": f"Prior workbook not found: {source_path}",
                    }
                ],
                "warnings": [],
            }
        )

    try:
        import openpyxl
    except ImportError as exc:
        return _json_result({"status": "ERROR", "message": f"openpyxl is not installed: {exc}"})

    out_dir = _resolve_workspace_path(run_dir)
    model_dir = _statement_model_dir(out_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = model_dir / "integrated_model.xlsx"
    if source_path.resolve() != workbook_path.resolve():
        shutil.copy2(source_path, workbook_path)

    update_scope = _json_loads(update_scope_json or "{}", "update_scope_json")
    if not isinstance(update_scope, dict):
        raise ValueError("update_scope_json must be a JSON object")
    model_input = _json_loads(model_input_json, "model_input_json") if model_input_json else {}
    if not isinstance(model_input, dict):
        raise ValueError("model_input_json must be a JSON object")
    statement_pack = (
        _json_loads(statement_spec_pack_json, "statement_spec_pack_json")
        if statement_spec_pack_json
        else _read_json_file(model_dir / "statement_spec_pack.json") or {}
    )
    if not isinstance(statement_pack, dict):
        raise ValueError("statement_spec_pack_json must be a JSON object")
    warnings = list(statement_pack.get("warnings") or [])
    if statement_pack.get("builder_blocked"):
        return _json_result(
            {
                "status": "FAIL",
                "workbook_path": "",
                "critical_count": int(statement_pack.get("critical_count") or 0),
                "critical": statement_pack.get("critical") or [],
                "warnings": statement_pack.get("warnings") or [],
                "message": "statement_spec_pack.json has critical findings; update is blocked.",
            }
        )

    wb = openpyxl.load_workbook(workbook_path)
    updated_cells: list[str] = []
    if model_input:
        try:
            merged = _merge_payload_model_input(model_input)
            historicals = _historical_records(merged)
        except ValueError as exc:
            warnings.append(
                {
                    "category": "Model Input",
                    "issue": f"Could not apply model_input_json to workbook: {exc}",
                }
            )
        else:
            period_ws = wb["Income Statement"] if "Income Statement" in wb.sheetnames else wb.active
            period_cols = {
                str(period_ws.cell(row=5, column=col_idx).value): col_idx
                for col_idx in range(3, period_ws.max_column + 1)
                if period_ws.cell(row=5, column=col_idx).value
            }
            update_map = {
                "Revenue Build": {
                    "core_revenue": "revenue",
                    "revenue_total": "revenue",
                },
                "Income Statement": {
                    "revenue_total": "revenue",
                    "gross_profit": "gross_profit",
                    "da_total": "da",
                    "ebit": "ebit",
                    "ebitda": "ebitda",
                    "interest_expense": "interest_expense",
                    "pretax_income": "pretax_income",
                    "tax_expense": "tax_expense",
                    "net_income": "net_income",
                    "diluted_shares": "shares",
                },
                "Balance Sheet": {
                    "cash_and_equivalents": "cash",
                    "accounts_receivable": "ar",
                    "inventory": "inventory",
                    "accounts_payable": "ap",
                    "net_ppe": "ppe",
                    "total_debt": "debt",
                    "retained_earnings": "retained_earnings",
                },
                "Cash Flow Statement": {
                    "net_income_cf": "net_income",
                    "da_addback": "da",
                    "capex": "capex",
                    "ending_cash": "cash",
                },
                "Working Capital": {
                    "accounts_receivable": "ar",
                    "inventory": "inventory",
                    "accounts_payable": "ap",
                },
                "PP&E & D&A": {
                    "capex": "capex",
                    "da_total": "da",
                    "ending_ppe": "ppe",
                },
                "Debt & Interest": {
                    "ending_debt": "debt",
                },
                "Share Count": {
                    "ending_diluted_shares": "shares",
                },
            }
            sheet_key_map = {
                "Revenue Build": "revenue_build",
                "Income Statement": "income_statement",
                "Balance Sheet": "balance_sheet",
                "Cash Flow Statement": "cash_flow",
                "Working Capital": "working_capital",
                "PP&E & D&A": "ppe_da",
                "Debt & Interest": "debt_interest",
                "Share Count": "share_count",
            }
            for record in historicals:
                col_idx = period_cols.get(str(record["period"]))
                if not col_idx:
                    warnings.append(
                        {
                            "category": "Period Mapping",
                            "issue": f"Workbook has no existing period column for {record['period']}.",
                        }
                    )
                    continue
                for sheet_name, row_to_field in update_map.items():
                    if sheet_name not in wb.sheetnames:
                        continue
                    ws = wb[sheet_name]
                    sheet_rows = DEFAULT_THREE_STATEMENT_ROW_MAP[
                        sheet_key_map[sheet_name]
                    ]
                    for row_key, field_name in row_to_field.items():
                        if field_name not in record or row_key not in sheet_rows:
                            continue
                        ws.cell(row=sheet_rows[row_key], column=col_idx, value=record[field_name])
                        updated_cells.append(
                            f"{sheet_name}!{_column_letter(col_idx)}{sheet_rows[row_key]}"
                        )

    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    if "Cover" in wb.sheetnames:
        cover = wb["Cover"]
        cover["A14"] = "Update Scope"
        cover["B14"] = json.dumps(update_scope, ensure_ascii=False)
        if model_input:
            cover["A15"] = "Updated Model Input"
            cover["B15"] = "financial_facts/task2_context_packet"
    wb.save(workbook_path)

    return _json_result(
        {
            "status": "OK",
            "workbook_path": _relative_to_workspace(workbook_path),
            "prior_workbook_path": _relative_to_workspace(source_path),
            "update_scope": update_scope,
            "updated_cells": updated_cells,
            "critical_count": 0,
            "warning_count": len(warnings),
            "critical": [],
            "warnings": warnings,
        }
    )


@tool
def validate_integrated_three_statement_model(
    excel_path: str,
    row_map_json: str = "",
) -> str:
    """Validate Task 2 integrated_model.xlsx for formula and tie-out discipline."""
    try:
        import openpyxl
    except ImportError as exc:
        return _json_result({"status": "ERROR", "message": f"openpyxl is not installed: {exc}"})

    path = _resolve_workspace_path(excel_path)
    if not path.exists():
        return _validation_result(
            "FAIL",
            [{"sheet": "", "cell": "", "category": "Missing File", "issue": f"Workbook not found: {path}"}],
            [],
        )

    row_map = DEFAULT_THREE_STATEMENT_ROW_MAP
    if row_map_json:
        parsed = _json_loads(row_map_json, "row_map_json")
        if isinstance(parsed, dict) and isinstance(parsed.get("row_map"), dict):
            row_map = parsed["row_map"]
        elif isinstance(parsed, dict):
            row_map = parsed

    wb = openpyxl.load_workbook(path, data_only=False)
    critical: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    for sheet_name in THREE_STATEMENT_TABS:
        if sheet_name not in wb.sheetnames:
            critical.append(
                {
                    "sheet": sheet_name,
                    "cell": "",
                    "category": "Missing Required Tab",
                    "issue": f"Required tab '{sheet_name}' is absent.",
                }
            )
    if critical:
        return _validation_result("FAIL", critical, warnings)

    defined_names = set(wb.defined_names)
    for name in REQUIRED_MODEL_NAMES:
        if name not in defined_names:
            critical.append(
                {
                    "sheet": "Assumptions",
                    "cell": name,
                    "category": "Missing Named Range",
                    "issue": f"Named range '{name}' is required.",
                }
            )

    checks = wb["Checks"]
    forecast_cols = [
        col_idx
        for col_idx in range(3, checks.max_column + 1)
        if str(checks.cell(row=4, column=col_idx).value or "").lower() == "forecast"
    ]
    if not forecast_cols:
        warnings.append(
            {
                "sheet": "Checks",
                "cell": "4:4",
                "category": "Period Metadata",
                "issue": "No forecast columns marked; validating all modeled columns.",
            }
        )
        forecast_cols = list(range(3, checks.max_column + 1))

    formula_requirements: list[tuple[str, list[int]]] = [
        ("Revenue Build", list(row_map["revenue_build"].values())),
        ("Income Statement", list(row_map["income_statement"].values())),
        ("Balance Sheet", list(row_map["balance_sheet"].values())),
        ("Cash Flow Statement", list(row_map["cash_flow"].values())),
        ("Working Capital", list(row_map["working_capital"].values())),
        ("PP&E & D&A", list(row_map["ppe_da"].values())),
        ("Debt & Interest", list(row_map["debt_interest"].values())),
        ("Share Count", list(row_map["share_count"].values())),
        ("DCF Inputs", list(row_map["dcf_inputs"].values())),
        ("Checks", [row for key, row in row_map["checks"].items() if key != "failing_check_count"]),
    ]
    for sheet_name, rows in formula_requirements:
        ws = wb[sheet_name]
        for row in sorted(set(rows)):
            for col_idx in forecast_cols:
                value = ws.cell(row=row, column=col_idx).value
                if not _formula(value):
                    critical.append(
                        {
                            "sheet": sheet_name,
                            "cell": f"{_column_letter(col_idx)}{row}",
                            "category": "Projection Hardcode",
                            "issue": "Forecast/model cell must be an Excel formula.",
                        }
                    )

    bs = wb["Balance Sheet"]
    cf = wb["Cash Flow Statement"]
    for col_idx in forecast_cols:
        col = _column_letter(col_idx)
        bs_cash = bs.cell(row=row_map["balance_sheet"]["cash_and_equivalents"], column=col_idx).value
        cf_cash = cf.cell(row=row_map["cash_flow"]["ending_cash"], column=col_idx).value
        if not (
            _formula(bs_cash)
            and "Cash Flow Statement" in bs_cash
            and f"{col}{row_map['cash_flow']['ending_cash']}" in bs_cash
        ):
            critical.append(
                {
                    "sheet": "Balance Sheet",
                    "cell": f"{col}{row_map['balance_sheet']['cash_and_equivalents']}",
                    "category": "Cash Tie-Out",
                    "issue": "Forecast BS cash must link to CF ending cash.",
                }
            )
        if not _formula(cf_cash):
            critical.append(
                {
                    "sheet": "Cash Flow Statement",
                    "cell": f"{col}{row_map['cash_flow']['ending_cash']}",
                    "category": "Cash Tie-Out",
                    "issue": "Forecast CF ending cash must be formula-driven.",
                }
            )

    dcf = wb["DCF Inputs"]
    for row in row_map["dcf_inputs"].values():
        for col_idx in forecast_cols:
            if not _formula(dcf.cell(row=row, column=col_idx).value):
                critical.append(
                    {
                        "sheet": "DCF Inputs",
                        "cell": f"{_column_letter(col_idx)}{row}",
                        "category": "DCF Input Hardcode",
                        "issue": "DCF Inputs must pull from linked model cells.",
                    }
                )

    return _validation_result("PASS" if not critical else "FAIL", critical, warnings)


@tool
def write_coverage_state(
    state_json: str,
    ticker: str,
    market: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
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
