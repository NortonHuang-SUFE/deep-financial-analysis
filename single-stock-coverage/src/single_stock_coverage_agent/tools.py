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
    if abs(parsed) > 1.5:
        return parsed / 100.0
    return parsed


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
    return f"'{sheet_name}'!{cell_ref}" if " " in sheet_name or "&" in sheet_name else f"{sheet_name}!{cell_ref}"


def _formula(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("=")


def _merge_payload_model_input(payload: dict[str, Any]) -> dict[str, Any]:
    facts = payload.get("financial_facts") if isinstance(payload.get("financial_facts"), dict) else {}
    merged = dict(facts)
    merged.update(payload)
    return merged


def _historical_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("historicals") or payload.get("historical_financials") or []
    if not isinstance(records, list):
        raise ValueError("model_input_json.historicals must be a list")
    if not records:
        raise ValueError("model_input_json must include at least one historical record")

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
        return [str(item) if str(item).upper().startswith("FY") else f"FY{item}E" for item in raw]

    summary = payload.get("projection_summary")
    if isinstance(summary, dict):
        raw = summary.get("forecast_years") or summary.get("periods")
        if isinstance(raw, list) and raw:
            return [str(item) if str(item).upper().startswith("FY") else f"FY{item}E" for item in raw]

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
        "operating_expenses": ("operating_expenses", "opex", "sgna", "selling_general_admin"),
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
        "nwc": ("nwc", "net_working_capital"),
        "capex": ("capex", "capital_expenditures"),
        "ppe": ("ppe", "net_ppe", "property_plant_equipment"),
        "debt": ("debt", "total_debt"),
        "retained_earnings": ("retained_earnings",),
        "shares": ("diluted_shares", "shares_outstanding", "shares"),
    }
    return _as_float(_field(record, *aliases.get(key, (key,))), 0.0)


def _assumption_set(payload: dict[str, Any], latest: dict[str, Any]) -> dict[str, float]:
    assumptions = payload.get("assumptions") if isinstance(payload.get("assumptions"), dict) else {}
    revenue = _historical_value(latest, "revenue")
    gross_profit = _historical_value(latest, "gross_profit")
    if gross_profit == 0 and _historical_value(latest, "ebit") != 0:
        gross_profit = revenue * 0.5
    opex = _historical_value(latest, "operating_expenses")
    da = _historical_value(latest, "da")
    capex = abs(_historical_value(latest, "capex"))
    pretax = _historical_value(latest, "pretax_income")
    tax = _historical_value(latest, "tax_expense")
    return {
        "revenue_growth": _as_decimal(assumptions.get("revenue_growth"), 0.05),
        "gross_margin": _as_decimal(assumptions.get("gross_margin"), _latest_ratio(gross_profit, revenue, 0.5)),
        "opex_pct_revenue": _as_decimal(assumptions.get("opex_pct_revenue"), _latest_ratio(opex, revenue, 0.2)),
        "tax_rate": _as_decimal(assumptions.get("tax_rate"), _latest_ratio(tax, pretax, 0.25)),
        "ar_days": _as_float(assumptions.get("ar_days"), 45.0),
        "inventory_pct_revenue": _as_decimal(assumptions.get("inventory_pct_revenue"), 0.1),
        "ap_days": _as_float(assumptions.get("ap_days"), 30.0),
        "da_pct_revenue": _as_decimal(assumptions.get("da_pct_revenue"), _latest_ratio(da, revenue, 0.03)),
        "capex_pct_revenue": _as_decimal(assumptions.get("capex_pct_revenue"), _latest_ratio(capex, revenue, 0.04)),
        "interest_rate": _as_decimal(assumptions.get("interest_rate"), 0.05),
        "debt_repayment_pct": _as_decimal(assumptions.get("debt_repayment_pct"), 0.0),
        "diluted_shares_growth": _as_decimal(assumptions.get("diluted_shares_growth"), 0.0),
        "dividend_payout_pct": _as_decimal(assumptions.get("dividend_payout_pct"), 0.0),
    }


def _validation_result(status: str, critical: list[dict[str, str]], warnings: list[dict[str, str]]) -> str:
    return json.dumps(
        {
            "status": status,
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "critical": critical,
            "warnings": warnings,
        },
        ensure_ascii=False,
        indent=2,
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
def build_integrated_three_statement_model(
    model_input_json: str,
    run_dir: str,
    output_dir: str = "./coverage",
) -> str:
    """Build Task 2 integrated_model.xlsx from structured Task 2 statement specs.

    Args:
        model_input_json: JSON object containing financial_facts/historicals,
            assumptions, and optional income_statement_spec, balance_sheet_spec,
            and cash_flow_spec returned by Task 2 child subagents.
        run_dir: Coverage run directory, absolute or workspace-relative.
        output_dir: Coverage root used only when resolving run_dir fallback.

    Returns:
        JSON with workbook_path, row_map, warnings, and unsourced_items.
    """
    try:
        import openpyxl
        from openpyxl.comments import Comment
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.workbook.defined_name import DefinedName
    except ImportError as exc:
        return json.dumps({"status": "ERROR", "message": f"openpyxl is not installed: {exc}"})

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
    model_dir = out_dir / "02_financial_model"
    model_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = model_dir / "integrated_model.xlsx"

    periods: list[dict[str, Any]] = [
        {"label": record["period"], "record": record, "is_actual": True}
        for record in historicals
    ]
    periods.extend({"label": label, "record": {}, "is_actual": False} for label in forecast_labels)
    period_columns = {period["label"]: _column_letter(idx + 3) for idx, period in enumerate(periods)}
    first_col = 3
    last_col = first_col + len(periods) - 1
    actual_count = len(historicals)

    styles = {
        "navy_fill": PatternFill("solid", fgColor="1F4E79"),
        "blue_fill": PatternFill("solid", fgColor="D9E1F2"),
        "gray_fill": PatternFill("solid", fgColor="F2F2F2"),
        "input_fill": PatternFill("solid", fgColor="EAF3F8"),
        "white_font": Font(name="Arial", bold=True, color="FFFFFF", size=11),
        "bold_font": Font(name="Arial", bold=True, color="000000", size=11),
        "input_font": Font(name="Arial", color="0000FF", size=11),
        "formula_font": Font(name="Arial", color="000000", size=11),
        "link_font": Font(name="Arial", color="008000", size=11),
        "normal_font": Font(name="Arial", color="000000", size=11),
        "center": Alignment(horizontal="center", vertical="center"),
        "left": Alignment(horizontal="left", vertical="center"),
        "thin_border": Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        ),
    }

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheets = {name: wb.create_sheet(name) for name in THREE_STATEMENT_TABS}
    row_map = json.loads(json.dumps(DEFAULT_THREE_STATEMENT_ROW_MAP))

    def set_title(ws, title: str) -> None:
        ws["A1"] = title
        ws["A1"].fill = styles["navy_fill"]
        ws["A1"].font = styles["white_font"]
        ws["A1"].alignment = styles["left"]
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(last_col, 6))
        ws["A3"] = f"Currency: {metadata['currency']} | Unit: {metadata['unit']}"
        ws["A3"].font = styles["normal_font"]

    def set_period_headers(ws) -> None:
        ws["A5"] = "Line Item"
        ws["B5"] = "Source / Type"
        ws["A5"].fill = styles["blue_fill"]
        ws["B5"].fill = styles["blue_fill"]
        ws["A5"].font = styles["bold_font"]
        ws["B5"].font = styles["bold_font"]
        for idx, period in enumerate(periods, start=first_col):
            cell = ws.cell(row=5, column=idx, value=period["label"])
            cell.fill = styles["blue_fill"]
            cell.font = styles["bold_font"]
            cell.alignment = styles["center"]
            type_cell = ws.cell(row=4, column=idx, value="Actual" if period["is_actual"] else "Forecast")
            type_cell.font = styles["bold_font"]
            type_cell.alignment = styles["center"]

    def format_sheet(ws) -> None:
        ws.freeze_panes = "C6"
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 18
        for col in range(first_col, last_col + 1):
            ws.column_dimensions[_column_letter(col)].width = 14
        for row in ws.iter_rows():
            for cell in row:
                cell.border = styles["thin_border"]
                if cell.alignment is None:
                    cell.alignment = styles["center"]

    def section(ws, row: int, title: str) -> None:
        ws.cell(row=row, column=1, value=title)
        for col in range(1, last_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = styles["navy_fill"]
            cell.font = styles["white_font"]

    def label(ws, row: int, text: str, source_type: str = "") -> None:
        ws.cell(row=row, column=1, value=text).font = styles["normal_font"]
        ws.cell(row=row, column=2, value=source_type).font = styles["normal_font"]

    def input_cell(cell, value: Any, source: str = "") -> None:
        cell.value = value
        cell.font = styles["input_font"]
        cell.fill = styles["input_fill"]
        cell.alignment = styles["center"]
        if source:
            cell.comment = Comment(f"Source: {source}", "single-stock-coverage")

    def formula_cell(cell, formula: str, link: bool = False) -> None:
        cell.value = formula
        cell.font = styles["link_font"] if link else styles["formula_font"]
        cell.alignment = styles["center"]

    def pct_row(ws, row: int) -> None:
        for col in range(first_col, last_col + 1):
            ws.cell(row=row, column=col).number_format = "0.0%"

    for ws in sheets.values():
        set_title(ws, ws.title)
        set_period_headers(ws)

    cover = sheets["Cover"]
    cover["A6"] = "Company"
    cover["B6"] = metadata["company"]
    cover["A7"] = "Ticker"
    cover["B7"] = metadata["ticker"]
    cover["A8"] = "Market"
    cover["B8"] = metadata["market"]
    cover["A9"] = "Fiscal Year End"
    cover["B9"] = metadata["fiscal_year_end"]
    cover["A10"] = "Model Date"
    cover["B10"] = datetime.now().strftime("%Y-%m-%d")
    cover["A12"] = "Artifact"
    cover["B12"] = "02_financial_model/integrated_model.xlsx"

    sources = sheets["Sources"]
    for col, header in enumerate(("Source ID", "Period", "Source", "Notes"), start=1):
        sources.cell(row=6, column=col, value=header).fill = styles["blue_fill"]
        sources.cell(row=6, column=col).font = styles["bold_font"]
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
    assumptions_ws["B6"] = "Base"
    input_cell(assumptions_ws["B6"], "Base", "Task2 assumption set")
    assumption_rows = {
        "Revenue Drivers": (9, {"Revenue Growth": (10, assumptions["revenue_growth"], "0.0%")}),
        "Margin Drivers": (
            13,
            {
                "Gross Margin": (14, assumptions["gross_margin"], "0.0%"),
                "Operating Expenses % Revenue": (15, assumptions["opex_pct_revenue"], "0.0%"),
                "Tax Rate": (16, assumptions["tax_rate"], "0.0%"),
            },
        ),
        "Working Capital Drivers": (
            19,
            {
                "AR Days": (20, assumptions["ar_days"], "0.0"),
                "Inventory % Revenue": (21, assumptions["inventory_pct_revenue"], "0.0%"),
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
                "Debt Repayment % Beginning Debt": (32, assumptions["debt_repayment_pct"], "0.0%"),
            },
        ),
        "Share Count Drivers": (
            35,
            {
                "Diluted Shares Growth": (36, assumptions["diluted_shares_growth"], "0.0%"),
                "Dividend Payout % Net Income": (37, assumptions["dividend_payout_pct"], "0.0%"),
            },
        ),
    }
    for title, (header_row, rows) in assumption_rows.items():
        section(assumptions_ws, header_row, title)
        for name, (row, value, fmt) in rows.items():
            label(assumptions_ws, row, name, "Input")
            for col in range(first_col + actual_count, last_col + 1):
                input_cell(assumptions_ws.cell(row=row, column=col), value, "Task2 child specs")
                assumptions_ws.cell(row=row, column=col).number_format = fmt

    def assumption_ref(row: int, col: int) -> str:
        return _sheet_ref("Assumptions", f"{_column_letter(col)}${row}".replace("$", ""))

    revenue_build = sheets["Revenue Build"]
    section(revenue_build, 7, "Revenue Build")
    label(revenue_build, 10, "Core Revenue", "Input / Formula")
    label(revenue_build, 12, "Total Revenue", "Formula")
    label(revenue_build, 13, "YoY Growth", "Formula")
    pct_row(revenue_build, 13)
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if period["is_actual"]:
            input_cell(
                revenue_build.cell(row=10, column=idx),
                _historical_value(period["record"], "revenue"),
                _source_for(period["record"]),
            )
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(revenue_build.cell(row=10, column=idx), f"={prev_col}12*(1+{_sheet_ref('Assumptions', f'{col}10')})")
        formula_cell(revenue_build.cell(row=12, column=idx), f"={col}10")
        if idx == first_col:
            formula_cell(revenue_build.cell(row=13, column=idx), "=0")
        else:
            formula_cell(revenue_build.cell(row=13, column=idx), f"=IF({prev_col}12=0,0,{col}12/{prev_col}12-1)")

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
            ar = _historical_value(record, "ar") or revenue * assumptions["ar_days"] / 365
            inventory = _historical_value(record, "inventory") or revenue * assumptions["inventory_pct_revenue"]
            ap = _historical_value(record, "ap") or revenue * assumptions["ap_days"] / 365
            for row, value in ((8, ar), (9, inventory), (10, ap)):
                input_cell(wc.cell(row=row, column=idx), value, _source_for(record))
            formula_cell(wc.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")
        else:
            formula_cell(wc.cell(row=8, column=idx), f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}20')}/365", True)
            formula_cell(wc.cell(row=9, column=idx), f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}21')}", True)
            formula_cell(wc.cell(row=10, column=idx), f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}22')}/365", True)
            formula_cell(wc.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")
        if idx == first_col:
            formula_cell(wc.cell(row=12, column=idx), "=0")
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(wc.cell(row=12, column=idx), f"={col}11-{prev_col}11")

    ppe = sheets["PP&E & D&A"]
    section(ppe, 7, "PP&E & D&A")
    for row, text in ((8, "Beginning PP&E"), (9, "CapEx"), (10, "D&A"), (11, "Ending PP&E")):
        label(ppe, row, text, "Input / Formula")
    for idx, period in enumerate(periods, start=first_col):
        col = _column_letter(idx)
        if idx == first_col:
            input_cell(ppe.cell(row=8, column=idx), _historical_value(period["record"], "ppe"), _source_for(period["record"]))
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(ppe.cell(row=8, column=idx), f"={prev_col}11")
        if period["is_actual"]:
            record = period["record"]
            input_cell(ppe.cell(row=9, column=idx), abs(_historical_value(record, "capex")), _source_for(record))
            input_cell(ppe.cell(row=10, column=idx), _historical_value(record, "da"), _source_for(record))
        else:
            formula_cell(ppe.cell(row=9, column=idx), f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}27')}", True)
            formula_cell(ppe.cell(row=10, column=idx), f"={_sheet_ref('Income Statement', f'{col}8')}*{_sheet_ref('Assumptions', f'{col}26')}", True)
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
            input_cell(debt.cell(row=8, column=idx), _historical_value(period["record"], "debt"), _source_for(period["record"]))
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(debt.cell(row=8, column=idx), f"={prev_col}11")
        if period["is_actual"]:
            input_cell(debt.cell(row=9, column=idx), 0, _source_for(period["record"]))
            input_cell(debt.cell(row=10, column=idx), 0, _source_for(period["record"]))
            input_cell(debt.cell(row=12, column=idx), _historical_value(period["record"], "interest_expense"), _source_for(period["record"]))
        else:
            formula_cell(debt.cell(row=9, column=idx), "=0")
            formula_cell(debt.cell(row=10, column=idx), f"={col}8*{_sheet_ref('Assumptions', f'{col}32')}")
            formula_cell(debt.cell(row=12, column=idx), f"=(({col}8+{col}11)/2)*{_sheet_ref('Assumptions', f'{col}31')}")
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
            input_cell(share.cell(row=8, column=idx), _historical_value(period["record"], "shares"), _source_for(period["record"]))
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(share.cell(row=8, column=idx), f"={prev_col}11")
        if period["is_actual"]:
            input_cell(share.cell(row=9, column=idx), 0, _source_for(period["record"]))
            input_cell(share.cell(row=10, column=idx), 0, _source_for(period["record"]))
            input_cell(share.cell(row=12, column=idx), _as_float(_field(period["record"], "dividends"), 0), _source_for(period["record"]))
            formula_cell(share.cell(row=11, column=idx), f"={col}8+{col}9-{col}10")
        else:
            formula_cell(share.cell(row=9, column=idx), "=0")
            formula_cell(share.cell(row=10, column=idx), "=0")
            formula_cell(share.cell(row=11, column=idx), f"={col}8*(1+{_sheet_ref('Assumptions', f'{col}36')})")
            formula_cell(share.cell(row=12, column=idx), f"=MAX(0,{_sheet_ref('Income Statement', f'{col}20')}*{_sheet_ref('Assumptions', f'{col}37')})", True)

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
            gross_profit = _historical_value(record, "gross_profit") or revenue * assumptions["gross_margin"]
            da = _historical_value(record, "da")
            ebit = _historical_value(record, "ebit") or gross_profit - _historical_value(record, "operating_expenses") - da
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
            formula_cell(income.cell(row=8, column=idx), f"={_sheet_ref('Revenue Build', f'{col}12')}", True)
            formula_cell(income.cell(row=9, column=idx), f"={col}8*(1-{_sheet_ref('Assumptions', f'{col}14')})")
            formula_cell(income.cell(row=10, column=idx), f"={col}8-{col}9")
            formula_cell(income.cell(row=12, column=idx), f"={col}8*{_sheet_ref('Assumptions', f'{col}15')}")
            formula_cell(income.cell(row=13, column=idx), f"={_sheet_ref('PP&E & D&A', f'{col}10')}", True)
            formula_cell(income.cell(row=14, column=idx), f"={col}10-{col}12-{col}13")
            formula_cell(income.cell(row=15, column=idx), f"={col}14+{col}13")
            formula_cell(income.cell(row=17, column=idx), f"={_sheet_ref('Debt & Interest', f'{col}12')}", True)
            formula_cell(income.cell(row=18, column=idx), f"={col}14-{col}17")
            formula_cell(income.cell(row=19, column=idx), f"=MAX(0,{col}18*{_sheet_ref('Assumptions', f'{col}16')})")
            formula_cell(income.cell(row=20, column=idx), f"={col}18-{col}19")
        formula_cell(income.cell(row=22, column=idx), f"={_sheet_ref('Share Count', f'{col}11')}", True)
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
            record = period["record"]
            input_cell(bs.cell(row=8, column=idx), _historical_value(record, "cash"), _source_for(record))
        else:
            formula_cell(bs.cell(row=8, column=idx), f"={_sheet_ref('Cash Flow Statement', f'{col}25')}", True)
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
            retained_earnings = _historical_value(period["record"], "retained_earnings")
            input_cell(bs.cell(row=25, column=idx), retained_earnings, _source_for(period["record"]))
        elif period["is_actual"]:
            input_cell(bs.cell(row=25, column=idx), _historical_value(period["record"], "retained_earnings"), _source_for(period["record"]))
        else:
            prev_col = _column_letter(idx - 1)
            formula_cell(bs.cell(row=25, column=idx), f"={prev_col}25+{_sheet_ref('Income Statement', f'{col}20')}-{_sheet_ref('Share Count', f'{col}12')}", True)
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
    for idx, period in enumerate(periods, start=first_col):
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
            formula_cell(cf.cell(row=24, column=idx), f"={_sheet_ref('Balance Sheet', f'{col}8')}-{col}23", True)
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
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None and cell.number_format == "General":
                    cell.number_format = "#,##0.0;(#,##0.0);-"
        format_sheet(ws)

    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(workbook_path)

    result = {
        "status": "OK",
        "workbook_path": _relative_to_workspace(workbook_path),
        "row_map": row_map,
        "period_columns": period_columns,
        "warnings": [],
        "unsourced_items": sorted(set(str(item) for item in unsourced_items)),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def validate_integrated_three_statement_model(
    excel_path: str,
    row_map_json: str = "",
) -> str:
    """Validate a Task 2 integrated three-statement workbook.

    Args:
        excel_path: Absolute or workspace-relative path to integrated_model.xlsx.
        row_map_json: Optional row map JSON returned by the builder. If omitted,
            the v1 fixed row-map contract is used.

    Returns:
        JSON validation report with Critical and Warning findings.
    """
    try:
        import openpyxl
    except ImportError as exc:
        return json.dumps({"status": "ERROR", "message": f"openpyxl is not installed: {exc}"})

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
        if isinstance(parsed, dict) and "row_map" in parsed and isinstance(parsed["row_map"], dict):
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
        ("Revenue Build", [row_map["revenue_build"]["core_revenue"], row_map["revenue_build"]["revenue_total"], row_map["revenue_build"]["revenue_growth"]]),
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
        bs_cash = bs.cell(row=row_map["balance_sheet"]["cash_and_equivalents"], column=col).value
        cf_cash = cf.cell(row=row_map["cash_flow"]["ending_cash"], column=col).value
        if not (_formula(bs_cash) and "Cash Flow Statement" in bs_cash and f"{col_letter}{row_map['cash_flow']['ending_cash']}" in bs_cash):
            critical.append(
                {
                    "sheet": "Balance Sheet",
                    "cell": f"{col_letter}{row_map['balance_sheet']['cash_and_equivalents']}",
                    "category": "Cash Tie-Out",
                    "issue": "Forecast BS cash must link to Cash Flow Statement ending cash.",
                }
            )
        if not _formula(cf_cash):
            critical.append(
                {
                    "sheet": "Cash Flow Statement",
                    "cell": f"{col_letter}{row_map['cash_flow']['ending_cash']}",
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

    status = "PASS" if not critical else "FAIL"
    return _validation_result(status, critical, warnings)


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
