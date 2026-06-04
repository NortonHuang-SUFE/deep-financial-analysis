"""Declarative topology for the single-stock-coverage agent family."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


LocalToolName = Literal[
    "create_coverage_run_dir",
    "write_markdown_artifact",
    "write_json_artifact",
    "update_run_manifest",
    "write_coverage_state",
    "build_integrated_three_statement_model",
    "validate_integrated_three_statement_model",
]
DCFBuilderToolName = Literal[
    "build_comps_excel",
    "build_dcf_model",
    "validate_dcf_model",
    "write_assumption_analysis",
    "write_valuation_summary",
]
SkillLibrary = Literal["single_stock_coverage", "dcf_builder"]
SkillRef = tuple[SkillLibrary, str]

ROOT_AGENT_NAME = "single_stock_coverage"

RUN_STATE_TOOLS: tuple[LocalToolName, ...] = (
    "create_coverage_run_dir",
    "update_run_manifest",
    "write_coverage_state",
)
ARTIFACT_WRITE_TOOLS: tuple[LocalToolName, ...] = (
    "create_coverage_run_dir",
    "write_markdown_artifact",
    "write_json_artifact",
    "update_run_manifest",
)
FINANCIAL_MODEL_TOOLS: tuple[LocalToolName, ...] = (
    "create_coverage_run_dir",
    "write_markdown_artifact",
    "write_json_artifact",
    "update_run_manifest",
    "build_integrated_three_statement_model",
    "validate_integrated_three_statement_model",
)
REPORT_STATE_TOOLS: tuple[LocalToolName, ...] = (
    "write_markdown_artifact",
    "write_json_artifact",
    "update_run_manifest",
    "write_coverage_state",
)
COMPANY_RESEARCH_MCP_SERVERS = (
    "ifind-stock",
    "ifind-news",
    "ifind-global-stock",
    "ifind-index",
    "ifind-edb",
)
FINANCIAL_MODEL_MCP_SERVERS = (
    "ifind-stock",
    "ifind-global-stock",
)
VALUATION_MCP_SERVERS = (
    "ifind-stock",
    "ifind-news",
    "ifind-edb",
    "ifind-global-stock",
    "ifind-index",
)
ALL_DCF_EXECUTION_TOOLS: tuple[DCFBuilderToolName, ...] = (
    "build_comps_excel",
    "build_dcf_model",
    "validate_dcf_model",
    "write_assumption_analysis",
    "write_valuation_summary",
)


DCF_EXECUTION_PROMPT = """# DCF Execution Subagent

You are the nested DCF execution subagent for Task 3 valuation. You only run
after the valuation analyst has produced and audited an assumption pack.

Your job is to convert audited DCF inputs into deterministic artifacts:

- comparable-company workbook when requested
- DCF model workbook with Bear/Base/Bull cases and three 5x5 sensitivity tables
- validation JSON / validation findings
- valuation summary

Use the local DCF tools when available. Treat the parent valuation analyst's
assumption pack as the source of scenario inputs. Do not invent missing
assumptions; return a clear blocker if required fields are absent.

Return a structured summary to the parent including:
- paths to dcf_model.xlsx, comps.xlsx, and any validation artifacts
- DCF equity value per share (Bear/Base/Bull)
- implied EV/EBITDA at Base case
- any validation warnings
"""


@dataclass(frozen=True)
class AgentSpec:
    """Single place to bind each agent to its prompt, tools, skills, and children."""

    name: str
    graph_name: str
    description: str
    prompt_file: str | None = None
    inline_prompt: str | None = None
    local_tools: tuple[LocalToolName, ...] = ()
    mcp_servers: tuple[str, ...] = ()
    dcf_tools: tuple[DCFBuilderToolName, ...] = ()
    skills: tuple[SkillRef, ...] = ()
    child_agents: tuple[str, ...] = ()
    parent: str | None = None
    level: int = 0

    def prompt_source(self) -> str:
        if self.prompt_file:
            return f"agents/{self.prompt_file}"
        return "inline_prompt"


AGENT_SPECS: dict[str, AgentSpec] = {
    ROOT_AGENT_NAME: AgentSpec(
        name=ROOT_AGENT_NAME,
        graph_name=ROOT_AGENT_NAME,
        description=(
            "Single-stock coverage orchestrator. Delegates company research, "
            "financial modeling, valuation, charting, and report assembly."
        ),
        prompt_file="single-stock-coverage.md",
        local_tools=RUN_STATE_TOOLS,
        child_agents=(
            "task1_company_researcher",
            "task2_financial_modeler",
            "task3_valuation_analyst",
            "task4_chart_pack_generator",
            "task5_report_assembler",
        ),
        level=0,
    ),
    "task1_company_researcher": AgentSpec(
        name="task1_company_researcher",
        graph_name="single_stock_coverage_task1_company_researcher",
        description=(
            "Task 1 Company Research: produces company_research.md, "
            "business_driver_map.json, and source_log.json for one target company."
        ),
        prompt_file="task1-company-researcher.md",
        local_tools=ARTIFACT_WRITE_TOOLS,
        mcp_servers=COMPANY_RESEARCH_MCP_SERVERS,
        skills=(("single_stock_coverage", "company-research"),),
        parent=ROOT_AGENT_NAME,
        level=1,
    ),
    "task2_financial_modeler": AgentSpec(
        name="task2_financial_modeler",
        graph_name="single_stock_coverage_task2_financial_modeler",
        description=(
            "Task 2 Financial Modeling: parent coordinator that delegates Income "
            "Statement, Balance Sheet, and Cash Flow Statement specs to three child "
            "subagents (is_modeler, bs_modeler, cf_modeler), then calls deterministic "
            "local tools to build/validate integrated_model.xlsx and writes model_audit.md."
        ),
        prompt_file="task2-financial-modeler.md",
        local_tools=FINANCIAL_MODEL_TOOLS,
        mcp_servers=FINANCIAL_MODEL_MCP_SERVERS,
        child_agents=("is_modeler", "bs_modeler", "cf_modeler"),
        skills=(
            ("single_stock_coverage", "financial-data-normalization"),
            ("single_stock_coverage", "xlsx-author"),
            ("single_stock_coverage", "three-statement-model"),
            ("single_stock_coverage", "audit-xls"),
            ("single_stock_coverage", "model-update"),
        ),
        parent=ROOT_AGENT_NAME,
        level=1,
    ),
    "is_modeler": AgentSpec(
        name="is_modeler",
        graph_name="single_stock_coverage_task2_is_modeler",
        description=(
            "Income Statement and Revenue Build modeler. Owned by Task 2 parent. "
            "Returns structured Revenue Build and Income Statement specs; does not "
            "write integrated_model.xlsx directly."
        ),
        prompt_file="task2-is-modeler.md",
        skills=(
            ("single_stock_coverage", "xlsx-author"),
            ("single_stock_coverage", "three-statement-model"),
        ),
        parent="task2_financial_modeler",
        level=2,
    ),
    "bs_modeler": AgentSpec(
        name="bs_modeler",
        graph_name="single_stock_coverage_task2_bs_modeler",
        description=(
            "Balance Sheet modeler. Owned by Task 2 parent. Returns a structured "
            "Balance Sheet spec after is_modeler completes; does not write Excel."
        ),
        prompt_file="task2-bs-modeler.md",
        skills=(
            ("single_stock_coverage", "xlsx-author"),
            ("single_stock_coverage", "three-statement-model"),
        ),
        parent="task2_financial_modeler",
        level=2,
    ),
    "cf_modeler": AgentSpec(
        name="cf_modeler",
        graph_name="single_stock_coverage_task2_cf_modeler",
        description=(
            "Cash Flow Statement modeler. Owned by Task 2 parent. Builds the Cash "
            "Flow Statement spec after is_modeler and bs_modeler complete, including "
            "cash tie-out dependencies; does not write Excel."
        ),
        prompt_file="task2-cf-modeler.md",
        skills=(
            ("single_stock_coverage", "xlsx-author"),
            ("single_stock_coverage", "three-statement-model"),
        ),
        parent="task2_financial_modeler",
        level=2,
    ),
    "task3_valuation_analyst": AgentSpec(
        name="task3_valuation_analyst",
        graph_name="single_stock_coverage_task3_valuation_analyst",
        description=(
            "Task 3 Valuation Analysis: parent that runs evidence gate, "
            "value-driver map, assumption audit, and valuation reconciliation. "
            "Delegates assumption generation to assumption_generator child and "
            "DCF/comps execution to dcf_execution child."
        ),
        prompt_file="task3-valuation-analyst.md",
        local_tools=ARTIFACT_WRITE_TOOLS,
        mcp_servers=VALUATION_MCP_SERVERS,
        child_agents=("assumption_generator", "dcf_execution"),
        skills=(
            ("single_stock_coverage", "valuation-methodologies"),
            ("single_stock_coverage", "dcf-assumption-generation"),
            ("single_stock_coverage", "assumption-audit"),
            ("single_stock_coverage", "valuation-reconciliation"),
        ),
        parent=ROOT_AGENT_NAME,
        level=1,
    ),
    "assumption_generator": AgentSpec(
        name="assumption_generator",
        graph_name="single_stock_coverage_task3_assumption_generator",
        description=(
            "DCF assumption generation subagent for Task 3. Receives the value driver map, "
            "Task 1 and Task 2 artifacts, and any assumption audit feedback. Returns a "
            "Bear/Base/Bull assumption pack (assumption_pack.md content) to the Task 3 parent."
        ),
        prompt_file="task3-assumption-generator.md",
        mcp_servers=VALUATION_MCP_SERVERS,
        skills=(("single_stock_coverage", "dcf-assumption-generation"),),
        parent="task3_valuation_analyst",
        level=2,
    ),
    "dcf_execution": AgentSpec(
        name="dcf_execution",
        graph_name="single_stock_coverage_task3_dcf_execution",
        description=(
            "Nested DCF executor for audited valuation assumptions. Builds comps "
            "and DCF workbooks with validation using current DCF-builder tool "
            "capability."
        ),
        inline_prompt=DCF_EXECUTION_PROMPT,
        dcf_tools=ALL_DCF_EXECUTION_TOOLS,
        skills=(
            ("dcf_builder", "dcf-model"),
            ("dcf_builder", "comps-analysis"),
            ("dcf_builder", "valuation-summary"),
            ("dcf_builder", "audit-xls"),
        ),
        parent="task3_valuation_analyst",
        level=2,
    ),
    "task4_chart_pack_generator": AgentSpec(
        name="task4_chart_pack_generator",
        graph_name="single_stock_coverage_task4_chart_pack_generator",
        description=(
            "Task 4 Chart Generation: creates a chart pack and chart_index.json "
            "from Task 1-3 artifacts without new research."
        ),
        prompt_file="task4-chart-pack-generator.md",
        local_tools=("write_json_artifact", "update_run_manifest"),
        skills=(("single_stock_coverage", "chart-pack"),),
        parent=ROOT_AGENT_NAME,
        level=1,
    ),
    "task5_report_assembler": AgentSpec(
        name="task5_report_assembler",
        graph_name="single_stock_coverage_task5_report_assembler",
        description=(
            "Task 5 Report Assembly: creates initiation reports or update memos "
            "from Task 1-4 artifacts without changing upstream conclusions."
        ),
        prompt_file="task5-report-assembler.md",
        local_tools=REPORT_STATE_TOOLS,
        skills=(("single_stock_coverage", "report-assembly"),),
        parent=ROOT_AGENT_NAME,
        level=1,
    ),
}


GRAPH_ENTRYPOINTS: dict[str, str] = {
    spec.graph_name: spec.name for spec in AGENT_SPECS.values()
}


def get_agent_spec(name: str) -> AgentSpec:
    try:
        return AGENT_SPECS[name]
    except KeyError as exc:
        known = ", ".join(sorted(AGENT_SPECS))
        raise KeyError(f"Unknown single-stock-coverage agent '{name}'. Known: {known}") from exc


def iter_agent_specs() -> tuple[AgentSpec, ...]:
    return tuple(sorted(AGENT_SPECS.values(), key=lambda spec: (spec.level, spec.name)))


def describe_agent_registry() -> list[dict]:
    """Return a human-readable, testable view of topology/tool/skill config."""
    return [
        {
            "name": spec.name,
            "graph_name": spec.graph_name,
            "parent": spec.parent,
            "level": spec.level,
            "prompt": spec.prompt_source(),
            "local_tools": list(spec.local_tools),
            "mcp_servers": list(spec.mcp_servers),
            "dcf_tools": list(spec.dcf_tools),
            "skills": [f"{library}:{skill}" for library, skill in spec.skills],
            "child_agents": list(spec.child_agents),
            "description": spec.description,
        }
        for spec in iter_agent_specs()
    ]
