"""Agent wiring registry for the single-stock coverage Deep Agents stack."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from financial_agent_runtime import (
    build_tool_catalog,
    describe_agent_tool_access,
    load_tool_access_config,
    mcp_server_names_for_tool_group,
    resolve_agent_tools,
)
from single_stock_coverage_agent.tools import (
    build_integrated_three_statement_model,
    create_coverage_run_dir,
    read_statement_context,
    reconcile_statement_specs,
    resolve_task2_handoff,
    update_integrated_three_statement_model,
    update_run_manifest,
    validate_balance_sheet_json,
    validate_cash_flow_json,
    validate_integrated_three_statement_model,
    validate_income_statement_json,
    verify_task2_artifacts,
    write_coverage_state,
    write_balance_sheet_json,
    write_cash_flow_json,
    write_income_statement_json,
    write_json_artifact,
    write_markdown_artifact,
    write_task2_model_audit,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
REGISTRY_PATH = AGENTS_DIR / "registry.yaml"
_DEEPAGENTS_HARNESS_PROFILE_REGISTERED = False


@dataclass(frozen=True)
class AgentSpec:
    name: str
    prompt: str
    description: str
    parent: str | None
    level: int
    role: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    excluded_builtin_tools: tuple[str, ...]
    skills: dict[str, tuple[str, ...]]
    subagents: tuple[str, ...]


@dataclass(frozen=True)
class AgentRegistry:
    skill_sources: dict[str, dict[str, Any]]
    agents: dict[str, AgentSpec]

    def agent(self, name: str) -> AgentSpec:
        try:
            return self.agents[name]
        except KeyError as exc:
            raise KeyError(f"Unknown single-stock-coverage agent: {name}") from exc

    def prompt_path(self, prompt: str) -> Path:
        return AGENTS_DIR / prompt

    def skill_source_path(self, source_name: str) -> Path:
        source = self.skill_sources[source_name]
        raw_path = Path(str(source["path"]))
        return raw_path if raw_path.is_absolute() else (PROJECT_ROOT / raw_path)


class ToolGroupResolver:
    """Resolves root-configured agent tool access to runtime tool objects."""

    def __init__(
        self,
        *,
        mcp_tool_groups: dict[str, list[Any]] | None = None,
        dynamic_tool_groups: dict[str, list[Any]] | None = None,
    ) -> None:
        self._access_config = load_tool_access_config(WORKSPACE_ROOT)
        self._local_tools = build_tool_catalog(_local_tools())
        self._mcp_tool_groups = dict(mcp_tool_groups or {})
        self._dynamic_tool_groups = dict(dynamic_tool_groups or {})

    def resolve_agent(self, agent_name: str) -> list[Any]:
        return resolve_agent_tools(
            agent_name,
            access_config=self._access_config,
            local_tools=self._local_tools,
            dynamic_tool_groups=self._dynamic_tool_groups,
            mcp_tool_groups=self._mcp_tool_groups,
        )


class SelectedSkillsMiddleware:
    """Skills middleware wrapper that exposes only configured skill names."""

    def __new__(
        cls,
        *,
        backend: Any,
        sources: list[tuple[str, str]],
        selected_skill_names: tuple[str, ...],
    ):
        from deepagents.middleware.skills import SkillsMiddleware

        class _SelectedSkillsMiddleware(SkillsMiddleware):
            def __init__(self) -> None:
                super().__init__(backend=backend, sources=sources)
                self._selected_skill_names = selected_skill_names

            def _filter_update(self, update):
                if update is None:
                    return None
                by_name = {skill["name"]: skill for skill in update["skills_metadata"]}
                update["skills_metadata"] = [
                    by_name[name]
                    for name in self._selected_skill_names
                    if name in by_name
                ]
                missing = sorted(set(self._selected_skill_names) - set(by_name))
                if missing:
                    errors = list(update.get("skills_load_errors", []))
                    errors.append(
                        "Configured skills not found: " + ", ".join(missing)
                    )
                    update["skills_load_errors"] = errors
                return update

            def before_agent(self, state, runtime, config):
                return self._filter_update(super().before_agent(state, runtime, config))

            async def abefore_agent(self, state, runtime, config):
                update = await super().abefore_agent(state, runtime, config)
                return self._filter_update(update)

        return _SelectedSkillsMiddleware()


def load_agent_registry(path: Path = REGISTRY_PATH) -> AgentRegistry:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("tool_groups"):
        raise ValueError(
            "single-stock-coverage tool_groups must be configured in the "
            "workspace root tool-concurrency.yaml, not agents/registry.yaml"
        )
    agents = {
        name: _parse_agent_spec(name, value or {})
        for name, value in (data.get("agents") or {}).items()
    }
    registry = AgentRegistry(
        skill_sources=data.get("skill_sources") or {},
        agents=agents,
    )
    validate_agent_registry(registry)
    return registry


def validate_agent_registry(registry: AgentRegistry) -> None:
    errors: list[str] = []
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    for agent_name, spec in registry.agents.items():
        prompt_path = registry.prompt_path(spec.prompt)
        if not prompt_path.exists():
            errors.append(f"{agent_name}: prompt not found: {prompt_path}")

        if agent_name not in access_config.agent_tools:
            errors.append(
                f"{agent_name}: missing root tool access config in "
                "tool-concurrency.yaml"
            )

        if spec.parent and spec.parent not in registry.agents:
            errors.append(f"{agent_name}: unknown parent: {spec.parent}")

        for source_name, skill_names in spec.skills.items():
            if source_name not in registry.skill_sources:
                errors.append(f"{agent_name}: unknown skill source: {source_name}")
                continue
            source_path = registry.skill_source_path(source_name)
            if not source_path.exists():
                errors.append(f"{agent_name}: skill source not found: {source_path}")
                continue
            for skill_name in skill_names:
                if not (source_path / skill_name / "SKILL.md").exists():
                    errors.append(
                        f"{agent_name}: skill not found: {source_name}/{skill_name}"
                    )

        for child_name in spec.subagents:
            if child_name not in registry.agents:
                errors.append(f"{agent_name}: unknown subagent: {child_name}")

    if errors:
        details = "\n- ".join(errors)
        raise ValueError(f"Invalid single-stock-coverage agent registry:\n- {details}")


def describe_agent(registry: AgentRegistry, agent_name: str) -> dict[str, Any]:
    spec = registry.agent(agent_name)
    tool_access = describe_agent_tool_access(
        load_tool_access_config(WORKSPACE_ROOT),
        agent_name,
    )
    return {
        "name": spec.name,
        "prompt": str(registry.prompt_path(spec.prompt)),
        "description": spec.description,
        "parent": spec.parent,
        "level": spec.level,
        "role": spec.role,
        "inputs": list(spec.inputs),
        "outputs": list(spec.outputs),
        "tool_groups": tool_access["tool_groups"],
        "direct_tools": tool_access["direct_tools"],
        "excluded_builtin_tools": list(spec.excluded_builtin_tools),
        "tools": tool_access["tools"],
        "skills": {
            source_name: list(skill_names)
            for source_name, skill_names in spec.skills.items()
        },
        "subagents": list(spec.subagents),
    }


def agent_uses_tool_group(
    registry: AgentRegistry,
    agent_name: str,
    group_name: str,
    *,
    recursive: bool = True,
) -> bool:
    registry.agent(agent_name)
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    if group_name in access_config.agent_tools[agent_name].tool_groups:
        return True
    if not recursive:
        return False
    spec = registry.agent(agent_name)
    return any(
        agent_uses_tool_group(registry, child_name, group_name, recursive=True)
        for child_name in spec.subagents
    )


def mcp_tool_group_names(registry: AgentRegistry) -> tuple[str, ...]:
    if not registry.agents:
        return ()
    access_config = load_tool_access_config(WORKSPACE_ROOT)
    return tuple(
        group_name
        for group_name, group in access_config.tool_groups.items()
        if group.source == "mcp"
    )


def mcp_tool_group_server_names(
    registry: AgentRegistry,
    group_name: str,
    all_server_names: list[str],
) -> set[str]:
    return mcp_server_names_for_tool_group(
        load_tool_access_config(WORKSPACE_ROOT),
        group_name,
        all_server_names,
    )


def create_registered_agent(
    agent_name: str,
    *,
    registry: AgentRegistry,
    model: Any | None = None,
    model_resolver: Callable[[str], Any] | None = None,
    tool_resolver: ToolGroupResolver,
    backend: Any | None = None,
    backend_resolver: Callable[[str], Any] | None = None,
    middleware: list[Any],
):
    from deepagents import create_deep_agent

    _ensure_deepagents_harness_profile()
    spec = registry.agent(agent_name)
    agent_model = model_resolver(agent_name) if model_resolver else model
    if agent_model is None:
        raise ValueError(f"No model configured for agent: {agent_name}")
    agent_backend = backend_resolver(agent_name) if backend_resolver else backend
    if agent_backend is None:
        raise ValueError(f"No backend configured for agent: {agent_name}")
    subagents = [
        create_registered_subagent_spec(
            child_name,
            registry=registry,
            model=agent_model,
            model_resolver=model_resolver,
            tool_resolver=tool_resolver,
            backend=agent_backend,
            backend_resolver=backend_resolver,
            middleware=middleware,
        )
        for child_name in spec.subagents
    ]
    return create_deep_agent(
        model=agent_model,
        system_prompt=_read_prompt(registry, spec.prompt),
        tools=tool_resolver.resolve_agent(spec.name),
        subagents=subagents,
        skills=None,
        middleware=(
            _skills_middleware(registry, spec, agent_backend)
            + list(middleware)
            + _builtin_tool_exclusion_middleware(spec)
        ),
        backend=agent_backend,
        name=spec.name,
    )


def _ensure_deepagents_harness_profile() -> None:
    global _DEEPAGENTS_HARNESS_PROFILE_REGISTERED
    if _DEEPAGENTS_HARNESS_PROFILE_REGISTERED:
        return
    from deepagents import (
        GeneralPurposeSubagentProfile,
        HarnessProfile,
        register_harness_profile,
    )

    register_harness_profile(
        "openai",
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )
    _DEEPAGENTS_HARNESS_PROFILE_REGISTERED = True


def create_registered_subagent_spec(
    agent_name: str,
    *,
    registry: AgentRegistry,
    model: Any | None = None,
    model_resolver: Callable[[str], Any] | None = None,
    tool_resolver: ToolGroupResolver,
    backend: Any | None = None,
    backend_resolver: Callable[[str], Any] | None = None,
    middleware: list[Any],
) -> dict[str, Any]:
    spec = registry.agent(agent_name)
    return {
        "name": spec.name,
        "description": spec.description,
        "runnable": create_registered_agent(
            agent_name,
            registry=registry,
            model=model,
            model_resolver=model_resolver,
            tool_resolver=tool_resolver,
            backend=backend,
            backend_resolver=backend_resolver,
            middleware=middleware,
        ),
    }


def _parse_agent_spec(name: str, data: dict[str, Any]) -> AgentSpec:
    if "tool_groups" in data:
        raise ValueError(
            f"{name}: tool_groups must be configured in the workspace root "
            "tool-concurrency.yaml"
        )
    skills = {
        source_name: tuple(skill_names or ())
        for source_name, skill_names in (data.get("skills") or {}).items()
    }
    return AgentSpec(
        name=name,
        prompt=str(data["prompt"]),
        description=str(data["description"]),
        parent=data.get("parent"),
        level=int(data.get("level", 0)),
        role=str(data.get("role", "")),
        inputs=tuple(str(item) for item in (data.get("inputs") or ())),
        outputs=tuple(str(item) for item in (data.get("outputs") or ())),
        excluded_builtin_tools=tuple(
            str(item) for item in (data.get("excluded_builtin_tools") or ())
        ),
        skills=skills,
        subagents=tuple(data.get("subagents") or ()),
    )


def _read_prompt(registry: AgentRegistry, prompt: str) -> str:
    path = registry.prompt_path(prompt)
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt not found at {path}")
    return path.read_text(encoding="utf-8")


def _skills_middleware(
    registry: AgentRegistry,
    spec: AgentSpec,
    backend: Any,
) -> list[Any]:
    if not spec.skills:
        return []

    from single_stock_coverage_agent.config import mirror_skills_into_backend

    sources: list[tuple[str, str]] = []
    selected_skill_names: list[str] = []
    for source_name, skill_names in spec.skills.items():
        if not skill_names:
            continue
        source = registry.skill_sources[source_name]
        label = str(source.get("label") or source_name.replace("_", " ").title())
        source_path = mirror_skills_into_backend(
            backend, registry.skill_source_path(source_name)
        )
        sources.append((source_path, label))
        selected_skill_names.extend(skill_names)

    if not selected_skill_names:
        return []

    return [
        SelectedSkillsMiddleware(
            backend=backend,
            sources=sources,
            selected_skill_names=tuple(selected_skill_names),
        )
    ]


def _builtin_tool_exclusion_middleware(spec: AgentSpec) -> list[Any]:
    if not spec.excluded_builtin_tools:
        return []

    from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware

    return [
        _ToolExclusionMiddleware(excluded=frozenset(spec.excluded_builtin_tools))
    ]


def _local_tools() -> list[Any]:
    tools = [
        build_integrated_three_statement_model,
        create_coverage_run_dir,
        read_statement_context,
        reconcile_statement_specs,
        resolve_task2_handoff,
        update_integrated_three_statement_model,
        update_run_manifest,
        validate_balance_sheet_json,
        validate_cash_flow_json,
        validate_integrated_three_statement_model,
        validate_income_statement_json,
        verify_task2_artifacts,
        write_coverage_state,
        write_balance_sheet_json,
        write_cash_flow_json,
        write_income_statement_json,
        write_json_artifact,
        write_markdown_artifact,
        write_task2_model_audit,
    ]
    return tools + _dcf_builder_tools()


def _dcf_builder_tools() -> list[Any]:
    try:
        from dcf_builder.tools import (
            build_comps_excel,
            build_dcf_model,
            validate_dcf_model,
            write_assumption_analysis,
            write_valuation_summary,
        )
    except Exception as exc:
        print(f"WARNING: DCF execution tools disabled: {exc}")
        return []

    return [
        build_comps_excel,
        build_dcf_model,
        validate_dcf_model,
        write_assumption_analysis,
        write_valuation_summary,
    ]
