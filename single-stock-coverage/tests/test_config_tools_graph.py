import asyncio
import importlib
import json

import single_stock_coverage_agent.config as config_module
from single_stock_coverage_agent.agent_registry import (
    ToolGroupResolver,
    agent_uses_tool_group,
    describe_agent,
    load_agent_registry,
)
from single_stock_coverage_agent.config import (
    PROJECT_ROOT,
    WORKSPACE_ROOT,
    enabled_mcp_server_configs,
    load_config,
)
from single_stock_coverage_agent import tools


def _statement_payload(statement_type: str) -> dict:
    canonical = {
        "income_statement": [
            "revenue_total",
            "gross_profit",
            "ebit",
            "ebitda",
            "interest_expense",
            "pretax_income",
            "tax_expense",
            "net_income",
            "da_total",
        ],
        "balance_sheet": [
            "cash_and_equivalents",
            "total_current_assets",
            "total_assets",
            "total_current_liabilities",
            "total_debt",
            "retained_earnings",
            "total_equity",
            "total_liabilities_and_equity",
        ],
        "cash_flow": [
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
        ],
    }[statement_type]
    dependencies = {
        "income_statement": [
            "revenue_build.total_revenue",
            "debt_interest.interest_expense",
            "share_count.diluted_shares",
        ],
        "balance_sheet": [
            "cash_flow.ending_cash",
            "income_statement.net_income",
            "share_count.dividends",
        ],
        "cash_flow": [
            "income_statement.net_income",
            "ppe_da.da_total",
            "balance_sheet.cash_and_equivalents",
        ],
    }[statement_type]
    payload = {
        "statement_type": statement_type,
        "canonical_row_keys": canonical,
        "line_items": [{"name": key} for key in canonical],
        "historical_inputs": [{"period": "FY2025A", "source": "annual report"}],
        "forecast_logic": {"method": "formula-driven"},
        "assumption_requirements": ["revenue growth"],
        "cross_statement_dependencies": dependencies,
        "source_coverage": {"status": "sourced"},
        "unsourced_items": [],
        "validation_status": "draft_checked",
    }
    if statement_type == "income_statement":
        payload["revenue_build_spec"] = {
            "statement_type": "revenue_build",
            "segments": [],
        }
    return payload


def _minimal_model_input() -> dict:
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
    }


def _agent_prompt(name: str) -> str:
    return (PROJECT_ROOT / "agents" / name).read_text(encoding="utf-8")


def _skill_text(name: str) -> str:
    return (PROJECT_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


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
        "SINGLE_STOCK_COVERAGE_TEST_MODE",
        "SINGLE_STOCK_COVERAGE_OUTPUT_TIMESTAMP",
    ]:
        monkeypatch.delenv(env_name, raising=False)


def test_default_config_resolves_from_project_root(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(config_module, "WORKSPACE_ENV_PATH", tmp_path / "missing.env")
    monkeypatch.chdir(tmp_path)

    cfg = load_config()

    assert PROJECT_ROOT.name == "single-stock-coverage"
    assert WORKSPACE_ROOT.name == "financialServicesModified"
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


def test_statement_json_tools_validate_write_and_read_context(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    tools._ACTIVE_RUNS.clear()
    monkeypatch.setattr(tools, "_workspace_root", lambda: tmp_path)
    run_dir = tmp_path / "coverage" / "us-exm" / "runs" / "20260604-120000"
    (run_dir / "01_company_research").mkdir(parents=True)
    (run_dir / "02_financial_model").mkdir(parents=True)
    (run_dir / "01_company_research" / "business_driver_map.json").write_text(
        '{"company": "Example Co", "ticker": "EXM"}',
        encoding="utf-8",
    )
    (run_dir / "01_company_research" / "source_log.json").write_text(
        '{"sources": ["annual report"]}',
        encoding="utf-8",
    )
    (run_dir / "02_financial_model" / "financial_facts.json").write_text(
        '{"historicals": [{"period": "FY2025A"}]}',
        encoding="utf-8",
    )
    (run_dir / "02_financial_model" / "task2_context_packet.json").write_text(
        '{"currency": "USD"}',
        encoding="utf-8",
    )

    context = json.loads(
        tools.read_statement_context.invoke(
            {"statement_type": "income_statement", "run_dir": str(run_dir)}
        )
    )
    assert context["statement_type"] == "income_statement"
    assert context["missing_artifacts"] == []
    assert "net_income" in context["canonical_row_keys"]

    income_json = json.dumps(_statement_payload("income_statement"))
    validation = json.loads(
        tools.validate_income_statement_json.invoke({"statement_json": income_json})
    )
    assert validation["status"] == "PASS"
    income_result = json.loads(
        tools.write_income_statement_json.invoke(
            {
                "statement_json": income_json,
                "ticker": "EXM",
                "market": "US",
                "run_dir": str(run_dir),
            }
        )
    )
    assert income_result["status"] == "OK"
    assert (run_dir / "02_financial_model" / "income_statement_spec.json").exists()
    assert (run_dir / "02_financial_model" / "revenue_build_spec.json").exists()

    balance_json = json.dumps(_statement_payload("balance_sheet"))
    assert json.loads(
        tools.validate_balance_sheet_json.invoke({"statement_json": balance_json})
    )["status"] == "PASS"
    tools.write_balance_sheet_json.invoke(
        {
            "statement_json": balance_json,
            "ticker": "EXM",
            "market": "US",
            "run_dir": str(run_dir),
        }
    )
    assert (run_dir / "02_financial_model" / "balance_sheet_spec.json").exists()

    cash_flow_json = json.dumps(_statement_payload("cash_flow"))
    assert json.loads(
        tools.validate_cash_flow_json.invoke({"statement_json": cash_flow_json})
    )["status"] == "PASS"
    tools.write_cash_flow_json.invoke(
        {
            "statement_json": cash_flow_json,
            "ticker": "EXM",
            "market": "US",
            "run_dir": str(run_dir),
        }
    )
    assert (run_dir / "02_financial_model" / "cash_flow_statement_spec.json").exists()

    bad_payload = _statement_payload("balance_sheet")
    bad_payload["canonical_row_keys"] = []
    bad_validation = json.loads(
        tools.validate_balance_sheet_json.invoke(
            {"statement_json": json.dumps(bad_payload)}
        )
    )
    assert bad_validation["status"] == "FAIL"
    assert bad_validation["critical_count"] > 0


def test_reconcile_statement_specs_writes_pack_and_preserves_warnings(
    monkeypatch, tmp_path
):
    _clear_env(monkeypatch)
    tools._ACTIVE_RUNS.clear()
    monkeypatch.setattr(tools, "_workspace_root", lambda: tmp_path)
    run_dir = tmp_path / "coverage" / "us-exm" / "runs" / "20260604-120000"
    (run_dir / "02_financial_model").mkdir(parents=True)

    income_json = json.dumps(_statement_payload("income_statement"))
    balance_payload = _statement_payload("balance_sheet")
    balance_payload["unsourced_items"] = ["retained_earnings bridge"]
    cash_flow_json = json.dumps(_statement_payload("cash_flow"))
    for tool_call, statement_json in (
        (tools.write_income_statement_json, income_json),
        (tools.write_balance_sheet_json, json.dumps(balance_payload)),
        (tools.write_cash_flow_json, cash_flow_json),
    ):
        result = json.loads(
            tool_call.invoke(
                {
                    "statement_json": statement_json,
                    "ticker": "EXM",
                    "market": "US",
                    "run_dir": str(run_dir),
                }
            )
        )
        assert result["status"] == "OK"

    result = json.loads(
        tools.reconcile_statement_specs.invoke(
            {"ticker": "EXM", "market": "US", "run_dir": str(run_dir)}
        )
    )

    pack_path = tmp_path / result["statement_spec_pack_path"]
    assert result["status"] == "PASS"
    assert result["builder_blocked"] is False
    assert result["critical_count"] == 0
    assert result["warning_count"] > 0
    assert pack_path.exists()
    assert json.loads(pack_path.read_text(encoding="utf-8"))["status"] == "PASS"


def test_integrated_three_statement_builder_and_validator(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    tools._ACTIVE_RUNS.clear()
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

    assert result["status"] == "OK"
    assert workbook_path.exists()
    assert result["row_map"]["income_statement"]["revenue_total"] == 8
    assert result["row_map"]["balance_sheet"]["cash_and_equivalents"] == 8
    assert result["row_map"]["cash_flow"]["ending_cash"] == 25
    assert result["period_columns"] == {
        "FY2023A": "C",
        "FY2024E": "D",
        "FY2025E": "E",
    }

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
    tools._ACTIVE_RUNS.clear()
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
    tools._ACTIVE_RUNS.clear()
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


def test_agent_registry_exposes_task2_parallel_statement_context():
    registry = load_agent_registry()

    task1 = describe_agent(registry, "task1_company_researcher")
    assert task1["tool_groups"] == ["mcp_tools", "local_artifact_tools"]
    assert task1["tools"]["local_artifact_tools"] == [
        "create_coverage_run_dir",
        "write_markdown_artifact",
        "write_json_artifact",
        "update_run_manifest",
        "write_coverage_state",
    ]
    assert task1["skills"] == {"single_stock_coverage": ["company-research"]}

    task2 = describe_agent(registry, "task2_financial_modeler")
    assert task2["parent"] == "single_stock_coverage"
    assert task2["level"] == 1
    assert task2["tool_groups"] == [
        "mcp_tools",
        "local_artifact_tools",
        "financial_model_builder_tools",
    ]
    assert task2["tools"]["financial_model_builder_tools"] == [
        "reconcile_statement_specs",
        "build_integrated_three_statement_model",
        "validate_integrated_three_statement_model",
    ]
    assert task2["skills"] == {
        "single_stock_coverage": [
            "financial-data-normalization",
            "three-statement-model",
            "statement-reconciliation-checks",
            "audit-xls",
        ]
    }
    assert task2["subagents"] == ["is_modeler", "bs_modeler", "cf_modeler"]

    is_modeler = describe_agent(registry, "is_modeler")
    assert is_modeler["parent"] == "task2_financial_modeler"
    assert is_modeler["level"] == 2
    assert is_modeler["tool_groups"] == ["income_statement_json_tools"]
    assert is_modeler["tools"]["income_statement_json_tools"] == [
        "read_statement_context",
        "validate_income_statement_json",
        "write_income_statement_json",
    ]
    assert is_modeler["skills"] == {
        "single_stock_coverage": ["income-statement-model", "statement-json-checks"]
    }
    assert "02_financial_model/income_statement_spec.json" in is_modeler["outputs"]

    bs_modeler = describe_agent(registry, "bs_modeler")
    assert bs_modeler["parent"] == "task2_financial_modeler"
    assert bs_modeler["level"] == 2
    assert bs_modeler["tool_groups"] == ["balance_sheet_json_tools"]
    assert bs_modeler["tools"]["balance_sheet_json_tools"] == [
        "read_statement_context",
        "validate_balance_sheet_json",
        "write_balance_sheet_json",
    ]
    assert bs_modeler["skills"] == {
        "single_stock_coverage": ["balance-sheet-model", "statement-json-checks"]
    }
    assert bs_modeler["outputs"] == ["02_financial_model/balance_sheet_spec.json"]
    assert not agent_uses_tool_group(registry, "bs_modeler", "mcp_tools")

    cf_modeler = describe_agent(registry, "cf_modeler")
    assert cf_modeler["parent"] == "task2_financial_modeler"
    assert cf_modeler["level"] == 2
    assert cf_modeler["tool_groups"] == ["cash_flow_json_tools"]
    assert cf_modeler["tools"]["cash_flow_json_tools"] == [
        "read_statement_context",
        "validate_cash_flow_json",
        "write_cash_flow_json",
    ]
    assert cf_modeler["skills"] == {
        "single_stock_coverage": ["cash-flow-model", "statement-json-checks"]
    }
    assert cf_modeler["outputs"] == [
        "02_financial_model/cash_flow_statement_spec.json"
    ]


def test_statement_json_tool_groups_resolve_runtime_tools():
    resolver = ToolGroupResolver(mcp_tools=[])

    assert [
        tool.name
        for tool in resolver.resolve(("income_statement_json_tools",))
    ] == [
        "read_statement_context",
        "validate_income_statement_json",
        "write_income_statement_json",
    ]
    assert [
        tool.name
        for tool in resolver.resolve(("balance_sheet_json_tools",))
    ] == [
        "read_statement_context",
        "validate_balance_sheet_json",
        "write_balance_sheet_json",
    ]
    assert [tool.name for tool in resolver.resolve(("cash_flow_json_tools",))] == [
        "read_statement_context",
        "validate_cash_flow_json",
        "write_cash_flow_json",
    ]
    assert [
        tool.name
        for tool in resolver.resolve(("financial_model_builder_tools",))
    ] == [
        "reconcile_statement_specs",
        "build_integrated_three_statement_model",
        "validate_integrated_three_statement_model",
    ]


def test_task2_prompts_are_json_first_with_parent_gates():
    parent = _agent_prompt("task2-financial-modeler.md")
    assert "run the three statement modeler subagents in parallel" in parent
    assert "reconcile_statement_specs" in parent
    assert "build_integrated_three_statement_model" in parent
    assert "validate_integrated_three_statement_model" in parent
    assert "Critical validation finding blocks Task 3 handoff" in parent

    prompt_expectations = {
        "task2-is-modeler.md": (
            "income_statement",
            "validate_income_statement_json",
            "write_income_statement_json",
        ),
        "task2-bs-modeler.md": (
            "balance_sheet",
            "validate_balance_sheet_json",
            "write_balance_sheet_json",
        ),
        "task2-cf-modeler.md": (
            "cash_flow",
            "validate_cash_flow_json",
            "write_cash_flow_json",
        ),
    }
    for prompt_name, (statement_type, validate_tool, write_tool) in prompt_expectations.items():
        prompt = _agent_prompt(prompt_name)
        assert f'statement_type="{statement_type}"' in prompt
        assert "Do not create, open, edit, or save `integrated_model.xlsx`" in prompt
        assert "Do not read sibling statement JSON" in prompt
        assert "statement-json-checks" in prompt
        assert validate_tool in prompt
        assert write_tool in prompt
        assert "row_map" not in prompt
        assert "populate the `" not in prompt
        assert "xlsx-author" not in prompt


def test_statement_skills_emphasize_checks_and_reconciliation_gates():
    for skill_name in [
        "income-statement-model",
        "balance-sheet-model",
        "cash-flow-model",
        "statement-json-checks",
    ]:
        text = _skill_text(skill_name)
        assert "Do not create, open, edit, or save `integrated_model.xlsx`" in text or (
            skill_name == "statement-json-checks"
        )
        assert "Critical" in text
        assert "source coverage" in text.lower()
        assert "canonical" in text.lower()

    reconciliation = _skill_text("statement-reconciliation-checks")
    assert "Critical findings block `build_integrated_three_statement_model`" in reconciliation
    assert "Cash Flow Statement `ending_cash`" in reconciliation
    assert "Income Statement `net_income`" in reconciliation
    assert "model_audit.md" in reconciliation


def test_root_langgraph_registers_single_stock_debug_entries():
    langgraph_config = json.loads((WORKSPACE_ROOT / "langgraph.json").read_text())

    assert (
        langgraph_config["graphs"]["single_stock_coverage_task2_bs_modeler"]
        == "./single-stock-coverage/src/single_stock_coverage_agent/graph.py:task2_bs_modeler_graph"
    )
    assert (
        langgraph_config["graphs"]["single_stock_coverage_task1_company_researcher"]
        == "./single-stock-coverage/src/single_stock_coverage_agent/graph.py:task1_company_researcher_graph"
    )


def test_graph_factories_import_in_test_mode(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("SINGLE_STOCK_COVERAGE_TEST_MODE", "1")
    import single_stock_coverage_agent.graph as graph_module

    graph_module = importlib.reload(graph_module)

    root_graph = asyncio.run(graph_module.graph())
    assert root_graph["name"] == "single_stock_coverage"
    assert root_graph["test_mode"] is True
    assert root_graph["agent_config"]["subagents"] == [
        "task1_company_researcher",
        "task2_financial_modeler",
        "task3_valuation_analyst",
        "task4_chart_pack_generator",
        "task5_report_assembler",
    ]

    bs_graph = asyncio.run(graph_module.task2_bs_modeler_graph())
    assert bs_graph["name"] == "bs_modeler"
    assert bs_graph["agent_config"]["parent"] == "task2_financial_modeler"
    assert bs_graph["agent_config"]["tool_groups"] == ["balance_sheet_json_tools"]
    assert bs_graph["agent_config"]["skills"] == {
        "single_stock_coverage": ["balance-sheet-model", "statement-json-checks"]
    }
