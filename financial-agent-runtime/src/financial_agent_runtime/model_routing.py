"""Workspace-level model routing for all agents and subagents."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

import yaml
from pydantic import BaseModel, ConfigDict, Field


MODEL_ROUTING_FILENAME = "model-routing.yaml"
DEFAULT_AGENT_NAMES: tuple[str, ...] = (
    "deep_orchestrator",
    "morning_note",
    "stock_screen",
    "sector_research",
    "thesis_tracker",
    "market_researcher",
    "html_image_renderer",
    "dcf_builder",
    "dcf-assumption-researcher",
    "single_stock_coverage",
    "task1_company_researcher",
    "task2_financial_modeler",
    "financial_facts_modeler",
    "is_modeler",
    "bs_modeler",
    "cf_modeler",
    "model_update_executor",
    "workbook_builder",
    "task3_valuation_analyst",
    "assumption_generator",
    "dcf_execution",
    "task4_chart_pack_generator",
    "task5_report_assembler",
)


class ModelProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    base_url: str
    api_key_env: str = ""
    max_tokens: int = 16000
    thinking: Literal["auto", "enabled", "disabled"] = "auto"


class ModelRoutingConfig(BaseModel):
    default_model: str = "qwen"
    models: dict[str, ModelProfile] = Field(default_factory=dict)
    agent_models: dict[str, str] = Field(default_factory=dict)


class ResolvedModelRoute(BaseModel):
    agent_name: str
    profile_name: str
    model: str
    base_url: str
    api_key_env: str
    api_key_present: bool
    max_tokens: int
    thinking: Literal["auto", "enabled", "disabled"]


def model_routing_path(workspace_root: str | Path) -> Path:
    return Path(workspace_root) / MODEL_ROUTING_FILENAME


def load_model_routing(
    workspace_root: str | Path,
    path: str | Path | None = None,
) -> ModelRoutingConfig:
    config_path = Path(path) if path else model_routing_path(workspace_root)
    if not config_path.exists():
        raise FileNotFoundError(f"Model routing config not found: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg = ModelRoutingConfig(**data)
    _validate_config_references(cfg)
    return cfg


def save_model_routing(
    workspace_root: str | Path,
    cfg: ModelRoutingConfig | dict[str, Any],
    path: str | Path | None = None,
) -> Path:
    config = cfg if isinstance(cfg, ModelRoutingConfig) else ModelRoutingConfig(**cfg)
    _validate_config_references(config)
    config_path = Path(path) if path else model_routing_path(workspace_root)
    config_path.write_text(
        yaml.safe_dump(
            config.model_dump(),
            allow_unicode=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def resolve_model_route(
    workspace_root: str | Path,
    agent_name: str,
    cfg: ModelRoutingConfig | None = None,
) -> ResolvedModelRoute:
    _load_workspace_env(workspace_root)
    config = cfg or load_model_routing(workspace_root)
    profile_name = config.agent_models.get(agent_name, config.default_model)
    try:
        profile = config.models[profile_name]
    except KeyError as exc:
        raise KeyError(
            f"Agent '{agent_name}' references unknown model profile '{profile_name}'."
        ) from exc

    return ResolvedModelRoute(
        agent_name=agent_name,
        profile_name=profile_name,
        model=profile.model,
        base_url=profile.base_url,
        api_key_env=profile.api_key_env,
        api_key_present=bool(_api_key_from_env(profile).strip()),
        max_tokens=profile.max_tokens,
        thinking=profile.thinking,
    )


def explain_model_routes(
    workspace_root: str | Path,
    agent_names: list[str] | tuple[str, ...] | None = None,
    cfg: ModelRoutingConfig | None = None,
) -> list[dict[str, Any]]:
    config = cfg or load_model_routing(workspace_root)
    names = tuple(agent_names or DEFAULT_AGENT_NAMES)
    return [
        resolve_model_route(workspace_root, agent_name, config).model_dump()
        for agent_name in names
    ]


def build_chat_model_for_agent(
    workspace_root: str | Path,
    agent_name: str,
    *,
    timeout: int = 120,
):
    route = resolve_model_route(workspace_root, agent_name)
    cfg = load_model_routing(workspace_root)
    profile = cfg.models[route.profile_name]
    api_key_env = profile.api_key_env.strip()
    if not api_key_env:
        raise ValueError(
            f"Missing api_key_env for model profile '{route.profile_name}'. "
            f"Set models.{route.profile_name}.api_key_env in "
            f"{model_routing_path(workspace_root)}."
        )
    api_key = _api_key_from_env(profile).strip()
    if not api_key:
        raise ValueError(
            f"Missing model API key for agent '{agent_name}'. "
            f"Set {api_key_env} in the workspace .env or process environment."
        )

    from langchain_openai import ChatOpenAI
    import httpx

    base_url = normalize_openai_compatible_base_url(route.base_url)
    parsed_base_url = urlparse(base_url)
    if not is_allowed_model_gateway(parsed_base_url):
        raise ValueError(
            "model base_url must be an HTTPS OpenAI-compatible gateway, "
            "or a local HTTP gateway on localhost/127.0.0.1."
        )

    model_kwargs: dict[str, Any] = {
        "model": route.model,
        "base_url": base_url,
        "api_key": api_key,
        "max_tokens": route.max_tokens,
        "streaming": False,
        "max_retries": 3,
        "timeout": timeout,
    }
    if parsed_base_url.netloc.lower() == "api.deepseek.com":
        thinking = route.thinking
        if thinking == "auto" and route.model.startswith("deepseek-v4"):
            thinking = "disabled"
        if thinking in {"enabled", "disabled"}:
            model_kwargs["extra_body"] = {"thinking": {"type": thinking}}

    proxy_url = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    if proxy_url:
        model_kwargs["http_async_client"] = httpx.AsyncClient(
            proxy=proxy_url,
            verify=False,
        )
        model_kwargs["http_client"] = httpx.Client(proxy=proxy_url, verify=False)

    return ChatOpenAI(**model_kwargs)


def validate_model_routing(
    workspace_root: str | Path,
    cfg: ModelRoutingConfig | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        config = cfg or load_model_routing(workspace_root)
    except Exception as exc:
        return [str(exc)]

    for profile_name, profile in config.models.items():
        if not profile.model.strip():
            errors.append(f"Model profile '{profile_name}' is missing model.")
        if not profile.base_url.strip():
            errors.append(f"Model profile '{profile_name}' is missing base_url.")
        if not profile.api_key_env.strip():
            errors.append(f"Model profile '{profile_name}' is missing api_key_env.")
        try:
            parsed = urlparse(normalize_openai_compatible_base_url(profile.base_url))
            if not is_allowed_model_gateway(parsed):
                errors.append(
                    f"Model profile '{profile_name}' has disallowed base_url: "
                    f"{profile.base_url}"
                )
        except Exception as exc:
            errors.append(f"Model profile '{profile_name}' has invalid base_url: {exc}")

    for agent_name, profile_name in sorted(config.agent_models.items()):
        if profile_name not in config.models:
            errors.append(
                f"Agent '{agent_name}' references unknown model profile "
                f"'{profile_name}'."
            )
    if config.default_model not in config.models:
        errors.append(
            f"default_model references unknown profile '{config.default_model}'."
        )
    return errors


def normalize_openai_compatible_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    path = parsed.path.rstrip("/")
    if _has_explicit_api_version(path):
        return normalized
    path = f"{path}/v1" if path else "/v1"
    return urlunparse(parsed._replace(path=path))


def is_allowed_model_gateway(parsed_base_url) -> bool:
    host = parsed_base_url.hostname or ""
    if parsed_base_url.scheme == "https" and parsed_base_url.netloc:
        return True
    return parsed_base_url.scheme == "http" and host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def _validate_config_references(cfg: ModelRoutingConfig) -> None:
    if cfg.default_model not in cfg.models:
        raise ValueError(
            f"default_model references unknown profile '{cfg.default_model}'."
        )
    unknown = sorted(
        {
            profile_name
            for profile_name in cfg.agent_models.values()
            if profile_name not in cfg.models
        }
    )
    if unknown:
        raise ValueError("Unknown model profile(s): " + ", ".join(unknown))


def _has_explicit_api_version(path: str) -> bool:
    parts = [part for part in path.strip("/").split("/") if part]
    return any(part.lower().startswith("v") and part[1:].isdigit() for part in parts)


def _api_key_from_env(profile: ModelProfile) -> str:
    env_name = profile.api_key_env.strip()
    if not env_name:
        return ""
    return os.getenv(env_name, "")


def _load_workspace_env(workspace_root: str | Path) -> None:
    env_path = Path(workspace_root) / ".env"
    if not env_path.exists():
        return
    from dotenv import load_dotenv

    load_dotenv(env_path, override=False)
