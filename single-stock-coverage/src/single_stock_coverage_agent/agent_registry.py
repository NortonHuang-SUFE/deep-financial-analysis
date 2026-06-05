"""Agent wiring registry for the single-stock coverage Deep Agents stack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from single_stock_coverage_agent.tools import (
    build_integrated_three_statement_model,
    create_coverage_run_dir,
    read_statement_context,
    reconcile_statement_specs,
    update_run_manifest,
    validate_balance_sheet_json,
    validate_cash_flow_json,
    validate_integrated_three_statement_model,
    validate_income_statement_json,
    write_coverage_state,
    write_balance_sheet_json,
    write_cash_flow_json,
    write_income_statement_json,
    write_json_artifact,
    write_markdown_artifact,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
REGISTRY_PATH = AGENTS_DIR / "registry.yaml"


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
    tool_groups: tuple[str, ...]
    skills: dict[str, tuple[str, ...]]
    subagents: tuple[str, ...]


@dataclass(frozen=True)
class AgentRegistry:
    tool_groups: dict[str, dict[str, Any]]
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
    """Resolves configured tool groups to runtime tool objects."""

    def __init__(self, *, mcp_tools: list[Any]) -> None:
        self._mcp_tools = list(mcp_tools)
        self._cache: dict[str, list[Any]] = {}

    def resolve(self, group_names: tuple[str, ...]) -> list[Any]:
        tools: list[Any] = []
        for group_name in group_names:
            tools.extend(self._resolve_group(group_name))
        return tools

    def _resolve_group(self, group_name: str) -> list[Any]:
        if group_name not in self._cache:
            if group_name == "local_artifact_tools":
                self._cache[group_name] = _local_artifact_tools()
            elif group_name == "mcp_tools":
                self._cache[group_name] = self._mcp_tools
            elif group_name == "dcf_execution_tools":
                self._cache[group_name] = _dcf_execution_tools()
            elif group_name == "financial_model_builder_tools":
                self._cache[group_name] = _financial_model_builder_tools()
            elif group_name == "income_statement_json_tools":
                self._cache[group_name] = _income_statement_json_tools()
            elif group_name == "balance_sheet_json_tools":
                self._cache[group_name] = _balance_sheet_json_tools()
            elif group_name == "cash_flow_json_tools":
                self._cache[group_name] = _cash_flow_json_tools()
            else:
                raise KeyError(f"Unknown tool group: {group_name}")
        return list(self._cache[group_name])


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
    agents = {
        name: _parse_agent_spec(name, value or {})
        for name, value in (data.get("agents") or {}).items()
    }
    registry = AgentRegistry(
        tool_groups=data.get("tool_groups") or {},
        skill_sources=data.get("skill_sources") or {},
        agents=agents,
    )
    validate_agent_registry(registry)
    return registry


def validate_agent_registry(registry: AgentRegistry) -> None:
    errors: list[str] = []
    for agent_name, spec in registry.agents.items():
        prompt_path = registry.prompt_path(spec.prompt)
        if not prompt_path.exists():
            errors.append(f"{agent_name}: prompt not found: {prompt_path}")

        if spec.parent and spec.parent not in registry.agents:
            errors.append(f"{agent_name}: unknown parent: {spec.parent}")

        for group_name in spec.tool_groups:
            if group_name not in registry.tool_groups:
                errors.append(f"{agent_name}: unknown tool group: {group_name}")

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
    return {
        "name": spec.name,
        "prompt": str(registry.prompt_path(spec.prompt)),
        "description": spec.description,
        "parent": spec.parent,
        "level": spec.level,
        "role": spec.role,
        "inputs": list(spec.inputs),
        "outputs": list(spec.outputs),
        "tool_groups": list(spec.tool_groups),
        "tools": {
            group_name: _configured_tool_names(registry, group_name)
            for group_name in spec.tool_groups
        },
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
    spec = registry.agent(agent_name)
    if group_name in spec.tool_groups:
        return True
    if not recursive:
        return False
    return any(
        agent_uses_tool_group(registry, child_name, group_name, recursive=True)
        for child_name in spec.subagents
    )


def create_registered_agent(
    agent_name: str,
    *,
    registry: AgentRegistry,
    model: Any,
    tool_resolver: ToolGroupResolver,
    backend: Any,
    middleware: list[Any],
):
    from deepagents import create_deep_agent

    spec = registry.agent(agent_name)
    subagents = [
        create_registered_subagent_spec(
            child_name,
            registry=registry,
            model=model,
            tool_resolver=tool_resolver,
            backend=backend,
            middleware=middleware,
        )
        for child_name in spec.subagents
    ]
    return create_deep_agent(
        model=model,
        system_prompt=_read_prompt(registry, spec.prompt),
        tools=tool_resolver.resolve(spec.tool_groups),
        subagents=subagents,
        skills=None,
        middleware=_skills_middleware(registry, spec, backend) + list(middleware),
        backend=backend,
        name=spec.name,
    )


def create_registered_subagent_spec(
    agent_name: str,
    *,
    registry: AgentRegistry,
    model: Any,
    tool_resolver: ToolGroupResolver,
    backend: Any,
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
            tool_resolver=tool_resolver,
            backend=backend,
            middleware=middleware,
        ),
    }


def _parse_agent_spec(name: str, data: dict[str, Any]) -> AgentSpec:
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
        tool_groups=tuple(data.get("tool_groups") or ()),
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

    sources: list[tuple[str, str]] = []
    selected_skill_names: list[str] = []
    for source_name, skill_names in spec.skills.items():
        if not skill_names:
            continue
        source = registry.skill_sources[source_name]
        label = str(source.get("label") or source_name.replace("_", " ").title())
        sources.append((str(registry.skill_source_path(source_name)), label))
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


def _configured_tool_names(registry: AgentRegistry, group_name: str) -> list[str]:
    group = registry.tool_groups[group_name]
    if "tools" in group:
        return list(group["tools"])
    if group_name == "mcp_tools":
        return ["<runtime MCP tools from enabled config.yaml servers>"]
    return [f"<{group.get('description', 'runtime tools')}>"]


def _local_artifact_tools() -> list[Any]:
    return [
        create_coverage_run_dir,
        write_markdown_artifact,
        write_json_artifact,
        update_run_manifest,
        write_coverage_state,
    ]


def _income_statement_json_tools() -> list[Any]:
    return [
        read_statement_context,
        validate_income_statement_json,
        write_income_statement_json,
    ]


def _balance_sheet_json_tools() -> list[Any]:
    return [
        read_statement_context,
        validate_balance_sheet_json,
        write_balance_sheet_json,
    ]


def _cash_flow_json_tools() -> list[Any]:
    return [
        read_statement_context,
        validate_cash_flow_json,
        write_cash_flow_json,
    ]


def _financial_model_builder_tools() -> list[Any]:
    return [
        reconcile_statement_specs,
        build_integrated_three_statement_model,
        validate_integrated_three_statement_model,
    ]


def _dcf_execution_tools() -> list[Any]:
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
