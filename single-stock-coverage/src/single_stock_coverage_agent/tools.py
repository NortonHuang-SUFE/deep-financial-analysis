"""Local artifact tools for the Single Stock Coverage agent."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TASK_SUBDIRS = (
    "01_company_research",
    "02_financial_model",
    "03_valuation",
    "04_charts",
    "05_report",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    return _project_root().parent


def _resolve_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    return path if path.is_absolute() else _workspace_root() / path


def _resolve_run_dir(run_dir: str) -> Path:
    path = Path(run_dir)
    return path if path.is_absolute() else _workspace_root() / path


def _relative_to_workspace(path: Path) -> str:
    try:
        return str(path.relative_to(_workspace_root()))
    except ValueError:
        return str(path)


def _coverage_ticker_dir(ticker: str, market: str, output_dir: str) -> Path:
    base = _resolve_output_dir(output_dir)
    return base / f"{market}-{ticker}"


def _get_run_timestamp() -> str:
    ts = os.getenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP")
    if ts:
        return ts
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def create_coverage_run_dir(
    ticker: str,
    market: str,
    output_dir: str = "./coverage",
) -> str:
    """Create a new timestamped run directory for a single-stock coverage run.

    Directory layout created:
        coverage/{market}-{ticker}/runs/{YYYYMMDD-HHMMSS}/
            01_company_research/
            02_financial_model/
            03_valuation/
            04_charts/chart_pack/
            05_report/

    Args:
        ticker: Stock ticker symbol (e.g. "600519").
        market: Market identifier (e.g. "A", "HK", "US").
        output_dir: Base coverage directory. Relative paths resolve from the
            workspace root. Defaults to ./coverage.

    Returns:
        Workspace-relative path to the newly created run directory.
    """
    ticker_dir = _coverage_ticker_dir(ticker, market, output_dir)
    timestamp = _get_run_timestamp()
    run_dir = ticker_dir / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create standard task subdirectories
    for subdir in _TASK_SUBDIRS:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    # chart_pack lives inside 04_charts
    (run_dir / "04_charts" / "chart_pack").mkdir(parents=True, exist_ok=True)

    return _relative_to_workspace(run_dir)


@tool
def write_coverage_state(
    ticker: str,
    market: str,
    state_json: str,
    output_dir: str = "./coverage",
) -> str:
    """Write or update the persistent coverage state file for a ticker.

    The state file is written to coverage/{market}-{ticker}/coverage_state.json
    and persists across individual runs. It records the latest company identity,
    coverage status, model path, valuation state, price target, rating,
    thesis pillars, key assumptions, next catalysts, and stale data flags.

    Args:
        ticker: Stock ticker symbol.
        market: Market identifier.
        state_json: Valid JSON string representing the coverage state.
        output_dir: Base coverage directory. Defaults to ./coverage.

    Returns:
        Workspace-relative path to the written coverage_state.json.
    """
    data: Any = json.loads(state_json)
    ticker_dir = _coverage_ticker_dir(ticker, market, output_dir)
    ticker_dir.mkdir(parents=True, exist_ok=True)
    state_path = ticker_dir / "coverage_state.json"
    state_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return _relative_to_workspace(state_path)


@tool
def read_coverage_state(
    ticker: str,
    market: str,
    output_dir: str = "./coverage",
) -> str:
    """Read the persistent coverage state for a ticker if it exists.

    Args:
        ticker: Stock ticker symbol.
        market: Market identifier.
        output_dir: Base coverage directory. Defaults to ./coverage.

    Returns:
        JSON string of the coverage state, or "{}" if no state file exists yet.
    """
    ticker_dir = _coverage_ticker_dir(ticker, market, output_dir)
    state_path = ticker_dir / "coverage_state.json"
    if not state_path.exists():
        return "{}"
    return state_path.read_text(encoding="utf-8")


@tool
def write_run_manifest(run_dir: str, manifest_json: str) -> str:
    """Write the run manifest into a coverage run directory.

    The manifest records the run id, ticker/market/company, task type
    (initiation/update/valuation refresh/model audit), triggering event,
    subagents called, input/output artifact paths, final conclusion,
    unsourced data list, and follow-up checklist.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory,
            as returned by create_coverage_run_dir.
        manifest_json: Valid JSON string for the run manifest.

    Returns:
        Workspace-relative path to the written run_manifest.json.
    """
    data: Any = json.loads(manifest_json)
    run_path = _resolve_run_dir(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    manifest_path = run_path / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return _relative_to_workspace(manifest_path)


@tool
def write_task_artifact(
    run_dir: str,
    task_subdir: str,
    filename: str,
    content: str,
) -> str:
    """Write a text artifact into a task subdirectory of a coverage run.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory.
        task_subdir: Task subdirectory name, one of:
            "01_company_research", "02_financial_model", "03_valuation",
            "04_charts", "05_report".
        filename: Name of the file to write (including extension).
        content: Text content to write.

    Returns:
        Workspace-relative path to the written file.
    """
    run_path = _resolve_run_dir(run_dir)
    dest_dir = run_path / task_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_text(content, encoding="utf-8")
    return _relative_to_workspace(dest_path)


@tool
def write_json_artifact(
    run_dir: str,
    task_subdir: str,
    filename: str,
    data_json: str,
) -> str:
    """Write a JSON artifact into a task subdirectory of a coverage run.

    Validates that data_json is parseable JSON and pretty-prints it before
    writing. Use this for structured data files such as business_driver_map.json,
    financial_facts.json, valuation_state.json, chart_index.json, etc.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory.
        task_subdir: Task subdirectory name, one of:
            "01_company_research", "02_financial_model", "03_valuation",
            "04_charts", "05_report".
        filename: Name of the JSON file to write (including .json extension).
        data_json: Valid JSON string to persist.

    Returns:
        Workspace-relative path to the written JSON file.
    """
    data: Any = json.loads(data_json)
    run_path = _resolve_run_dir(run_dir)
    dest_dir = run_path / task_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = filename if filename.endswith(".json") else f"{filename}.json"
    dest_path = dest_dir / safe_name
    dest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return _relative_to_workspace(dest_path)


@tool
def read_task_artifact(
    run_dir: str,
    task_subdir: str,
    filename: str,
) -> str:
    """Read a text or JSON artifact from a task subdirectory of a coverage run.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory.
        task_subdir: Task subdirectory name (e.g. "01_company_research").
        filename: Name of the file to read.

    Returns:
        File content as a string, or "[FILE NOT FOUND]" if the file does not exist.
    """
    run_path = _resolve_run_dir(run_dir)
    target = run_path / task_subdir / filename
    if not target.exists():
        return "[FILE NOT FOUND]"
    return target.read_text(encoding="utf-8")


@tool
def list_run_artifacts(run_dir: str) -> str:
    """List all files under a coverage run directory.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory.

    Returns:
        JSON array of workspace-relative paths for every file found under
        run_dir. Returns an empty JSON array "[]" if the directory does not exist.
    """
    run_path = _resolve_run_dir(run_dir)
    if not run_path.exists():
        return "[]"
    paths = sorted(
        _relative_to_workspace(p) for p in run_path.rglob("*") if p.is_file()
    )
    return json.dumps(paths, ensure_ascii=False)


@tool
def build_excel_model(
    run_dir: str,
    task_subdir: str,
    filename: str,
    description: str,
) -> str:
    """Create a minimal Excel workbook stub for financial modeling.

    Produces a workbook with two sheets:
    - "Cover": contains the description text and basic metadata.
    - "Checks": a placeholder sheet for model integrity checks (BS balance,
      cash tie-out, NI link, RE roll-forward, CapEx/PP&E tie, debt tie).

    This is a stub. The agent is expected to fill in additional sheets and
    Excel formulas using iFind MCP data for historical facts and assumption-
    driven forecasts.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory.
        task_subdir: Task subdirectory name (e.g. "02_financial_model").
        filename: Name of the xlsx file to create (including .xlsx extension).
        description: Description or title text to write on the Cover sheet.

    Returns:
        Workspace-relative path to the created xlsx file.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for build_excel_model. "
            "Install it with: pip install openpyxl"
        ) from exc

    run_path = _resolve_run_dir(run_dir)
    dest_dir = run_path / task_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = filename if filename.endswith(".xlsx") else f"{filename}.xlsx"
    dest_path = dest_dir / safe_name

    wb = openpyxl.Workbook()

    # --- Cover sheet ---
    cover = wb.active
    cover.title = "Cover"
    cover["A1"] = description
    cover["A1"].font = Font(bold=True, size=14)
    cover["A3"] = "Generated by single-stock-coverage agent"
    cover["A4"] = f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    cover["A6"] = (
        "NOTE: This is a model stub. Fill in historical data and formulas "
        "using iFind MCP data. All projections, subtotals, and checks must "
        "use Excel formulas — only hard-code sourced historical facts and "
        "assumption drivers."
    )

    # --- Checks sheet ---
    checks = wb.create_sheet("Checks")
    checks["A1"] = "Model Integrity Checks"
    checks["A1"].font = Font(bold=True)
    check_items = [
        "BS Balance (Assets = Liabilities + Equity)",
        "Cash Tie-Out (Opening + CF = Closing)",
        "NI Link (IS Net Income = BS Retained Earnings delta + Dividends)",
        "RE Roll-Forward",
        "CapEx / PP&E Tie",
        "Debt Tie (Opening + Drawdowns - Repayments = Closing)",
    ]
    for row_idx, item in enumerate(check_items, start=3):
        checks.cell(row=row_idx, column=1, value=item)
        checks.cell(row=row_idx, column=2, value="[FORMULA REQUIRED]")

    wb.save(dest_path)
    return _relative_to_workspace(dest_path)


@tool
def audit_excel_model(
    run_dir: str,
    task_subdir: str,
    filename: str,
) -> str:
    """Audit an Excel model for basic structural integrity.

    Checks performed:
    - The workbook has at least 3 sheets.
    - The workbook contains a sheet named "Checks" or "Check".
    - The file size is greater than 0 bytes.

    Args:
        run_dir: Workspace-relative (or absolute) path to the run directory.
        task_subdir: Task subdirectory name (e.g. "02_financial_model").
        filename: Name of the xlsx file to audit.

    Returns:
        JSON string with audit results:
        {"passed": bool, "sheets": [...sheet names...], "issues": [...strings...]}
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for audit_excel_model. "
            "Install it with: pip install openpyxl"
        ) from exc

    run_path = _resolve_run_dir(run_dir)
    file_path = run_path / task_subdir / filename

    issues: list[str] = []

    if not file_path.exists():
        result = {
            "passed": False,
            "sheets": [],
            "issues": [f"File not found: {_relative_to_workspace(file_path)}"],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    file_size = file_path.stat().st_size
    if file_size == 0:
        issues.append("File size is 0 bytes.")

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_names: list[str] = wb.sheetnames
        wb.close()
    except Exception as exc:
        result = {
            "passed": False,
            "sheets": [],
            "issues": [f"Failed to open workbook: {exc}"],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    if len(sheet_names) < 3:
        issues.append(
            f"Workbook has only {len(sheet_names)} sheet(s); expected at least 3."
        )

    has_checks = any(s.lower() in ("checks", "check") for s in sheet_names)
    if not has_checks:
        issues.append(
            'No "Checks" or "Check" sheet found. '
            "A Checks sheet is required for model integrity validation."
        )

    passed = len(issues) == 0
    result = {
        "passed": passed,
        "sheets": sheet_names,
        "issues": issues,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
