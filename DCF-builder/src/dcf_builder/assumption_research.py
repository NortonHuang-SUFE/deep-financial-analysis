"""DCF assumption research subagent configuration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dcf_builder.config import (
    DEFAULT_ASSUMPTION_MCP_SERVER_NAMES,
    PROJECT_ROOT,
    file_storage_root,
)


ASSUMPTION_SUBAGENT_NAME = "dcf-assumption-researcher"
ASSUMPTION_SKILLS_ROOT = (
    PROJECT_ROOT / "subagents" / ASSUMPTION_SUBAGENT_NAME / "skills"
)
ASSUMPTION_PROMPT_PATH = PROJECT_ROOT / "agents" / f"{ASSUMPTION_SUBAGENT_NAME}.md"

ASSUMPTION_MCP_SERVER_NAMES = DEFAULT_ASSUMPTION_MCP_SERVER_NAMES

ASSUMPTION_SCENARIO_NAMES = ("Bear", "Base", "Bull")
ASSUMPTION_REQUIRED_FIELDS = (
    "revenue_growth",
    "ebit_margin",
    "tax_rate",
    "da_pct_revenue",
    "capex_pct_revenue",
    "nwc_pct_delta_revenue",
    "wacc",
    "terminal_growth",
    "source",
)


def load_assumption_research_prompt() -> str:
    """Load the assumption researcher's system prompt."""
    if not ASSUMPTION_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Assumption researcher prompt not found at {ASSUMPTION_PROMPT_PATH}"
        )
    return ASSUMPTION_PROMPT_PATH.read_text(encoding="utf-8")


def assumption_result_contract() -> str:
    """Return the scenario schema the parent agent must pass to the subagent."""
    fields = "\n".join(f"- `{field}`" for field in ASSUMPTION_REQUIRED_FIELDS)
    scenarios = ", ".join(f"`{name}`" for name in ASSUMPTION_SCENARIO_NAMES)
    return (
        "The final answer must include top-level sections in this exact order: "
        "`## 假设背景`, `## 假设结果`, and `## 假设逻辑`. "
        "`## 假设逻辑` must be the final and most important section, explaining "
        "how the evidence leads to each assumption. The result does not need to "
        f"be JSON, but it must contain assumption data for {scenarios}. "
        "Each scenario should cover:\n"
        f"{fields}\n"
        "`revenue_growth` and `ebit_margin` should contain five annual values "
        "when possible. Other fields may be scalar values or annual values. "
        "`terminal_growth` must be lower than `wacc`. If the user asks for an "
        "assumption analysis artifact, write this Markdown pack with "
        "`write_assumption_analysis` in the shared output directory and return "
        "the artifact path."
    )


def create_assumption_research_subagent_spec(
    *,
    model: Any,
    tools: Sequence[Any] | None = None,
    middleware: Sequence[Any] | None = None,
    backend: Any | None = None,
) -> dict[str, Any]:
    """Create the compiled Deep Agents subagent spec used by the parent."""
    runnable = create_assumption_research_agent(
        model=model,
        tools=tools,
        middleware=middleware,
        backend=backend,
    )
    return {
        "name": ASSUMPTION_SUBAGENT_NAME,
        "description": (
            "Use after comparable-company analysis and before build_dcf_model. "
            "Researches target, peer, industry, macro, news, and announcement "
            "evidence, then returns Bear/Base/Bull DCF assumptions as Markdown "
            "with enough data for the parent to build `dcf_json.scenarios`; "
            "writes the assumption analysis artifact when requested."
        ),
        "runnable": runnable,
    }


def create_assumption_research_agent(
    *,
    model: Any,
    tools: Sequence[Any] | None = None,
    middleware: Sequence[Any] | None = None,
    backend: Any | None = None,
):
    """Create a standalone Deep Agent for testing or direct assumption research."""
    from deepagents import create_deep_agent
    from deepagents.backends import LocalShellBackend

    if backend is None:
        backend = LocalShellBackend(
            root_dir=str(file_storage_root()),
            virtual_mode=False,
            inherit_env=True,
        )

    return create_deep_agent(
        model=model,
        system_prompt=load_assumption_research_prompt(),
        tools=list(tools or []),
        skills=[str(ASSUMPTION_SKILLS_ROOT)],
        middleware=list(middleware or []),
        backend=backend,
        name=ASSUMPTION_SUBAGENT_NAME,
    )


def assumption_task_brief_template() -> str:
    """Template guidance for the parent agent's `task` description."""
    return (
        "Call `task` with `subagent_type` "
        f"`{ASSUMPTION_SUBAGENT_NAME}`. The task description must summarize "
        "all evidence collected so far, especially target-company historicals, "
        "peer/company data, comps outputs, market data, industry observations, "
        "sources, any `[UNSOURCED]` gaps, the shared output directory, and "
        "whether the user requested an assumption analysis artifact. It must "
        f"also include this output contract:\n\n{assumption_result_contract()}"
    )
