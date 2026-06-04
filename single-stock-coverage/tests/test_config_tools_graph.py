import importlib
import json
from types import SimpleNamespace

import single_stock_coverage_agent.config as config_module
import single_stock_coverage_agent.factory as factory_module
from single_stock_coverage_agent.agent_registry import (
    GRAPH_ENTRYPOINTS,
    ROOT_AGENT_NAME,
    get_agent_spec,
    describe_agent_registry,
)
from single_stock_coverage_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    load_config,
)
from single_stock_coverage_agent import tools


TASK2_MODEL_TOOL_NAMES = [
    "create_coverage_run_dir",
    "write_markdown_artifact",
    "write_json_artifact",
    "update_run_manifest",
    "build_integrated_three_statement_model",
    "validate_integrated_three_statement_model",
]


def _minimal_model_input():
    return {
        "company": "Example Co",
        "ticker": "EXM",
        "market": "US",
        "currency": "USD",
        "unit": "millions",
        "fiscal_year_end": "Dec",
        "projection_periods": 2,
        "historicals": [
            {
                "period": "FY2023A",
                "year": 2023,
                "revenue": 1000,
                "gross_profit": 500,
                "operating_expenses": 180,
                "da": 30,
                "ebit": 290,
                "ebitda": 320,
                "interest_expense": 10,
                "pretax_income": 280,
                "tax_expense": 70,
                "net_income": 210,
                "capex": 45,
                "cash": 120,
                "debt": 200,
                "retained_earnings": 300,
                "shares": 100,
                "source": "FY2023 annual report",
            }
        ],
        "assumptions": {
            "revenue_growth": 0.05,
            "gross_margin": 0.5,
            "opex_pct_revenue": 0.18,
            "tax_rate": 0.25,
            "da_pct_revenue": 0.03,
            "capex_pct_revenue": 0.04,
        },
        "revenue_build_spec": {"segments": ["Core"]},
        "income_statement_spec": {"line_items": ["Revenue", "EBIT", "Net Income"]},
        "balance_sheet_spec": {"line_items": ["Cash", "Debt", "Equity"]},
        "cash_flow_spec": {"line_items": ["CFO", "CFI", "CFF", "Ending Cash"]},
    }


def _clear_env(monkeypatch):
    for env_name in [
        "MODEL_NAME",
        "MODEL_GATEWAY_BASE_URL",
        "MODEL_GATEWAY_API_KEY",
        "MODEL_RELAY_BASE_URL",
        "MODEL_RELAY_API_KEY",
        "MODEL_BASE_URL",
        "MODEL_API_KEY",
        "MODEL_THINKING",
        "MODEL_MAX_TOKENS",
        "DASHSCOPE_API_KEY",
        "ALIBABA_API_KEY",
        "IFIND_MCP_AUTHORIZATION",
        "IFIND_MCP_TOKEN",
        "SINGLE_STOCK_COVERAGE_DISABLE_MCP",
        "SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP",
    ]:
        monkeypatch.delenv(env_name, raising=False)


def test_default_config_resolves_from_project_root(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", tmp_path / "missing.env")
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "single-stock-coverage"
    assert WORKSPACE_ROOT == PROJECT_ROOT.parent
    assert cfg.model.default == "qwen-3.7-max"
    assert cfg.output.dir == "./coverage"
    assert "ifind-stock" in cfg.mcp


def test_workspace_env_and_process_env_override_ifind_auth(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    workspace_env = tmp_path / ".env"
    workspace_env.write_text("IFIND_MCP_TOKEN=from-workspace-env\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", workspace_env)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mcp:
  ifind-stock:
    url: "https://example.test/stock"
    transport: "streamable_http"
""",
        encoding="utf-8",
    )

    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"] == {
        "Authorization": "Bearer from-workspace-env"
    }

    monkeypatch.setenv("IFIND_MCP_AUTHORIZATION", "from-process-env")
    cfg = load_config(str(config_path))
    server_configs = enabled_mcp_server_configs(cfg)

    assert server_configs["ifind-stock"]["headers"] == {
        "Authorization": "from-process-env"
    }


def test_coverage_run_and_artifact_tools(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    tools._ACTIVE_RUNS.clear()
    monkeypatch.setattr(tools, "_workspace_root", lambda: tmp_path)
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP", "20260604-120000")

    result_json = tools.create_coverage_run_dir.invoke(
        {
            "company": "测试公司",
            "ticker": "000001.SZ",
            "market": "A-share",
            "task_type": "initiation",
            "triggering_event": "",
        }
    )
    result = json.loads(result_json)

    assert result["run_dir"] == "coverage/a-share-000001.sz/runs/20260604-120000"
    manifest_path = tmp_path / result["manifest_path"]
    state_path = tmp_path / result["coverage_state_path"]
    assert manifest_path.exists()
    assert state_path.exists()

    md_path = tools.write_markdown_artifact.invoke(
        {
            "markdown": "# Test\n",
            "filename": "company_research.md",
            "subdir": "01_company_research",
            "ticker": "000001.SZ",
            "market": "A-share",
            "run_dir": result["run_dir"],
        }
    )
    json_path = tools.write_json_artifact.invoke(
        {
            "data_json": '{"ticker": "000001.SZ"}',
            "filename": "business_driver_map.json",
            "subdir": "01_company_research",
            "ticker": "000001.SZ",
            "market": "A-share",
            "run_dir": result["run_dir"],
        }
    )

    assert (tmp_path / md_path).read_text(encoding="utf-8") == "# Test\n"
    assert json.loads((tmp_path / json_path).read_text(encoding="utf-8")) == {
        "ticker": "000001.SZ"
    }

    manifest_result = tools.update_run_manifest.invoke(
        {
            "patch_json": '{"subagents_called": ["task1_company_researcher"]}',
            "ticker": "000001.SZ",
            "market": "A-share",
            "run_dir": result["run_dir"],
        }
    )
    manifest = json.loads((tmp_path / manifest_result).read_text(encoding="utf-8"))
    assert manifest["subagents_called"] == ["task1_company_researcher"]


def test_integrated_three_statement_builder_and_validator(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    tools._ACTIVE_RUNS.clear()
    monkeypatch.setattr(tools, "_workspace_root", lambda: tmp_path)

    run_dir = tmp_path / "coverage" / "us-exm" / "runs" / "20260604-120000"
    run_dir.mkdir(parents=True)

    result_json = tools.build_integrated_three_statement_model.invoke(
        {
            "model_input_json": json.dumps(_minimal_model_input()),
            "run_dir": str(run_dir),
        }
    )
    result = json.loads(result_json)
    workbook_path = tmp_path / result["workbook_path"]

    assert workbook_path.exists()
    assert result["row_map"]["income_statement"]["revenue_total"] == 8
    assert result["row_map"]["balance_sheet"]["cash_and_equivalents"] == 8
    assert result["row_map"]["cash_flow"]["ending_cash"] == 25

    import openpyxl

    wb = openpyxl.load_workbook(workbook_path, data_only=False)
    assert wb.sheetnames == list(tools.THREE_STATEMENT_TABS)
    assert all(name in set(wb.defined_names) for name in tools.REQUIRED_MODEL_NAMES)
    assert wb["DCF Inputs"]["D8"].value.startswith("=")
    assert wb["Checks"]["D9"].value.startswith("=")

    validation = json.loads(
        tools.validate_integrated_three_statement_model.invoke(
            {
                "excel_path": str(workbook_path),
                "row_map_json": json.dumps(result["row_map"]),
            }
        )
    )
    assert validation["status"] == "PASS"
    assert validation["critical_count"] == 0


def test_integrated_three_statement_validator_flags_missing_tab(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(tools, "_workspace_root", lambda: tmp_path)
    run_dir = tmp_path / "coverage" / "us-exm" / "runs" / "20260604-120000"
    run_dir.mkdir(parents=True)
    result = json.loads(
        tools.build_integrated_three_statement_model.invoke(
            {
                "model_input_json": json.dumps(_minimal_model_input()),
                "run_dir": str(run_dir),
            }
        )
    )
    workbook_path = tmp_path / result["workbook_path"]

    import openpyxl

    wb = openpyxl.load_workbook(workbook_path)
    del wb["Checks"]
    wb.save(workbook_path)

    validation = json.loads(
        tools.validate_integrated_three_statement_model.invoke(
            {"excel_path": str(workbook_path)}
        )
    )
    assert validation["status"] == "FAIL"
    assert validation["critical"][0]["category"] == "Missing Required Tab"


def test_integrated_three_statement_validator_flags_hardcode_and_cash_break(
    monkeypatch, tmp_path
):
    _clear_env(monkeypatch)
    monkeypatch.setattr(tools, "_workspace_root", lambda: tmp_path)
    run_dir = tmp_path / "coverage" / "us-exm" / "runs" / "20260604-120000"
    run_dir.mkdir(parents=True)
    result = json.loads(
        tools.build_integrated_three_statement_model.invoke(
            {
                "model_input_json": json.dumps(_minimal_model_input()),
                "run_dir": str(run_dir),
            }
        )
    )
    workbook_path = tmp_path / result["workbook_path"]

    import openpyxl

    wb = openpyxl.load_workbook(workbook_path, data_only=False)
    wb["Income Statement"]["D8"] = 1234
    wb["Balance Sheet"]["D8"] = 555
    wb.save(workbook_path)

    validation = json.loads(
        tools.validate_integrated_three_statement_model.invoke(
            {
                "excel_path": str(workbook_path),
                "row_map_json": json.dumps(result["row_map"]),
            }
        )
    )
    categories = {item["category"] for item in validation["critical"]}
    assert validation["status"] == "FAIL"
    assert "Projection Hardcode" in categories
    assert "Cash Tie-Out" in categories


def test_graph_imports_in_test_mode(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_TEST_MODE", "1")
    import single_stock_coverage_agent.graph as graph_module

    assert graph_module.graph["name"] == ROOT_AGENT_NAME
    assert graph_module.graph["test_mode"] is True
    assert graph_module.graph["child_agents"] == [
        "task1_company_researcher",
        "task2_financial_modeler",
        "task3_valuation_analyst",
        "task4_chart_pack_generator",
        "task5_report_assembler",
    ]


def test_standalone_subagent_graph_imports_in_test_mode(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_TEST_MODE", "1")

    modules = {
        "single_stock_coverage_agent.graphs.task1_company_researcher": "task1_company_researcher",
        "single_stock_coverage_agent.graphs.task2_financial_modeler": "task2_financial_modeler",
        "single_stock_coverage_agent.graphs.task2_is_modeler": "is_modeler",
        "single_stock_coverage_agent.graphs.task2_bs_modeler": "bs_modeler",
        "single_stock_coverage_agent.graphs.task2_cf_modeler": "cf_modeler",
        "single_stock_coverage_agent.graphs.task3_valuation_analyst": "task3_valuation_analyst",
        "single_stock_coverage_agent.graphs.task3_assumption_generator": "assumption_generator",
        "single_stock_coverage_agent.graphs.task3_dcf_execution": "dcf_execution",
        "single_stock_coverage_agent.graphs.task4_chart_pack_generator": "task4_chart_pack_generator",
        "single_stock_coverage_agent.graphs.task5_report_assembler": "task5_report_assembler",
    }

    imported = {
        agent_name: importlib.import_module(module_path)
        for module_path, agent_name in modules.items()
    }
    task2_module = importlib.import_module(
        "single_stock_coverage_agent.graphs.task2_financial_modeler"
    )
    dcf_module = importlib.import_module(
        "single_stock_coverage_agent.graphs.task3_dcf_execution"
    )

    assert {name: module.graph["name"] for name, module in imported.items()} == {
        name: name for name in modules.values()
    }
    assert task2_module.graph["name"] == "task2_financial_modeler"
    assert task2_module.graph["child_agents"] == [
        "is_modeler",
        "bs_modeler",
        "cf_modeler",
    ]
    assert task2_module.graph["local_tools"] == TASK2_MODEL_TOOL_NAMES
    assert dcf_module.graph["name"] == "dcf_execution"
    assert dcf_module.graph["dcf_tools"] == [
        "build_comps_excel",
        "build_dcf_model",
        "validate_dcf_model",
        "write_assumption_analysis",
        "write_valuation_summary",
    ]
    assert dcf_module.graph["skills"] == [
        "dcf_builder:dcf-model",
        "dcf_builder:comps-analysis",
        "dcf_builder:valuation-summary",
        "dcf_builder:audit-xls",
    ]


def test_agent_registry_describes_full_nested_topology():
    registry = {entry["name"]: entry for entry in describe_agent_registry()}

    assert registry[ROOT_AGENT_NAME]["child_agents"] == [
        "task1_company_researcher",
        "task2_financial_modeler",
        "task3_valuation_analyst",
        "task4_chart_pack_generator",
        "task5_report_assembler",
    ]
    assert registry["task2_financial_modeler"]["child_agents"] == [
        "is_modeler",
        "bs_modeler",
        "cf_modeler",
    ]
    assert registry["task2_financial_modeler"]["local_tools"] == TASK2_MODEL_TOOL_NAMES
    assert registry["task3_valuation_analyst"]["child_agents"] == [
        "assumption_generator",
        "dcf_execution",
    ]
    assert registry["task1_company_researcher"]["mcp_servers"] == [
        "ifind-stock",
        "ifind-news",
        "ifind-global-stock",
        "ifind-index",
        "ifind-edb",
    ]
    assert registry["task4_chart_pack_generator"]["mcp_servers"] == []
    assert registry["task5_report_assembler"]["mcp_servers"] == []
    assert registry["is_modeler"]["local_tools"] == []
    assert registry["is_modeler"]["skills"] == [
        "single_stock_coverage:xlsx-author",
        "single_stock_coverage:three-statement-model",
    ]
    assert registry["dcf_execution"]["skills"] == [
        "dcf_builder:dcf-model",
        "dcf_builder:comps-analysis",
        "dcf_builder:valuation-summary",
        "dcf_builder:audit-xls",
    ]


def test_factory_resolves_agent_specific_tools_and_skill_views(monkeypatch, tmp_path):
    monkeypatch.setattr(factory_module, "SKILL_VIEW_ROOT", tmp_path / "skill-views")
    context = factory_module.AgentBuildContext(
        model=None,
        local_tools_by_name={
            "create_coverage_run_dir": SimpleNamespace(name="create_coverage_run_dir"),
            "write_markdown_artifact": SimpleNamespace(name="write_markdown_artifact"),
            "write_json_artifact": SimpleNamespace(name="write_json_artifact"),
            "update_run_manifest": SimpleNamespace(name="update_run_manifest"),
            "write_coverage_state": SimpleNamespace(name="write_coverage_state"),
            "build_integrated_three_statement_model": SimpleNamespace(
                name="build_integrated_three_statement_model"
            ),
            "validate_integrated_three_statement_model": SimpleNamespace(
                name="validate_integrated_three_statement_model"
            ),
        },
        mcp_tools_by_server={
            "ifind-stock": [SimpleNamespace(name="stock_mcp")],
            "ifind-news": [SimpleNamespace(name="news_mcp")],
            "ifind-global-stock": [SimpleNamespace(name="global_stock_mcp")],
            "ifind-index": [SimpleNamespace(name="index_mcp")],
        },
        dcf_tools_by_name={
            "build_comps_excel": SimpleNamespace(name="build_comps_excel"),
            "build_dcf_model": SimpleNamespace(name="build_dcf_model"),
            "validate_dcf_model": SimpleNamespace(name="validate_dcf_model"),
            "write_assumption_analysis": SimpleNamespace(name="write_assumption_analysis"),
            "write_valuation_summary": SimpleNamespace(name="write_valuation_summary"),
        },
        backend=None,
        middleware=[],
    )

    is_tools = factory_module._tools_for_spec(get_agent_spec("is_modeler"), context)
    task2_tools = factory_module._tools_for_spec(
        get_agent_spec("task2_financial_modeler"), context
    )
    chart_tools = factory_module._tools_for_spec(
        get_agent_spec("task4_chart_pack_generator"), context
    )
    dcf_tools = factory_module._tools_for_spec(get_agent_spec("dcf_execution"), context)

    assert is_tools == []
    assert [tool.name for tool in task2_tools] == TASK2_MODEL_TOOL_NAMES + [
        "stock_mcp",
        "global_stock_mcp",
    ]
    assert [tool.name for tool in chart_tools] == [
        "write_json_artifact",
        "update_run_manifest",
    ]
    assert [tool.name for tool in dcf_tools] == [
        "build_comps_excel",
        "build_dcf_model",
        "validate_dcf_model",
        "write_assumption_analysis",
        "write_valuation_summary",
    ]

    sources = factory_module._skill_sources_for_spec(get_agent_spec("is_modeler"))
    assert sources == [str(tmp_path / "skill-views" / "is_modeler")]
    assert sorted(path.name for path in (tmp_path / "skill-views" / "is_modeler").iterdir()) == [
        "three-statement-model",
        "xlsx-author",
    ]


def test_root_langgraph_registers_all_single_stock_coverage_graphs():
    root_config_path = WORKSPACE_ROOT / "langgraph.json"
    root_config = json.loads(root_config_path.read_text(encoding="utf-8"))
    registered = root_config["graphs"]

    for graph_name in GRAPH_ENTRYPOINTS:
        assert graph_name in registered

    assert registered[ROOT_AGENT_NAME] == (
        "./single-stock-coverage/src/single_stock_coverage_agent/graph.py:graph"
    )
    assert registered["single_stock_coverage_task3_dcf_execution"].endswith(
        "/graphs/task3_dcf_execution.py:graph"
    )
