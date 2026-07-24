"""Workspace-level model routing for all agents and subagents."""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

import yaml
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field


MODEL_ROUTING_FILENAME = "model-routing.yaml"
DEFAULT_AGENT_NAMES: tuple[str, ...] = (
    "daily_report",
    "morning_note",
    "html_image_renderer",
)


class ModelProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    base_url: str
    api_key_env: str = ""
    max_tokens: int = 16000
    thinking: Literal["auto", "enabled", "disabled"] = "auto"
    reasoning_effort: Literal["low", "medium", "high", "max", "xhigh"] | None = None


class AgentModelRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = None
    multimodal_fallback_model: str | None = None


class ModelRoutingConfig(BaseModel):
    default_model: str = "qwen"
    default_multimodal_model: str | None = None
    models: dict[str, ModelProfile] = Field(default_factory=dict)
    agent_models: dict[str, str | AgentModelRoute] = Field(default_factory=dict)


class ResolvedModelRoute(BaseModel):
    agent_name: str
    profile_name: str
    model: str
    base_url: str
    api_key_env: str
    api_key_present: bool
    max_tokens: int
    thinking: Literal["auto", "enabled", "disabled"]
    reasoning_effort: Literal["low", "medium", "high", "max", "xhigh"] | None
    multimodal_fallback_profile_name: str | None = None
    multimodal_fallback_model: str | None = None
    multimodal_fallback_base_url: str | None = None
    multimodal_fallback_api_key_env: str | None = None
    multimodal_fallback_api_key_present: bool = False
    multimodal_fallback_max_tokens: int | None = None
    multimodal_fallback_thinking: Literal["auto", "enabled", "disabled"] | None = None
    multimodal_fallback_reasoning_effort: (
        Literal["low", "medium", "high", "max", "xhigh"] | None
    ) = None


class ChatModelWithFallbacks(BaseChatModel):
    """BaseChatModel-compatible wrapper for primary/fallback chat models."""

    primary: BaseChatModel
    fallbacks: tuple[BaseChatModel, ...] = Field(default_factory=tuple)

    @property
    def _llm_type(self) -> str:
        return f"{self.primary._llm_type}-with-fallbacks"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._invoke_candidates("_generate", messages, stop, run_manager, kwargs)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_exc: Exception | None = None
        for model in self._candidate_models():
            try:
                return await model._agenerate(
                    messages,
                    stop=stop,
                    run_manager=run_manager,
                    **kwargs,
                )
            except Exception as exc:
                last_exc = exc
        raise RuntimeError("No chat models configured for fallback routing.") from last_exc

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | dict | bool | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        primary = self.primary.bind_tools(tools, tool_choice=tool_choice, **kwargs)
        fallbacks = [
            model.bind_tools(tools, tool_choice=tool_choice, **kwargs)
            for model in self.fallbacks
        ]
        return primary.with_fallbacks(fallbacks)

    def _get_ls_params(
        self,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.primary._get_ls_params(stop=stop, **kwargs)

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "primary": getattr(self.primary, "_identifying_params", {}),
            "fallbacks": [
                getattr(model, "_identifying_params", {}) for model in self.fallbacks
            ],
        }

    def _candidate_models(self) -> tuple[BaseChatModel, ...]:
        return (self.primary, *self.fallbacks)

    def _invoke_candidates(
        self,
        method_name: str,
        messages: list[BaseMessage],
        stop: list[str] | None,
        run_manager: Any | None,
        kwargs: dict[str, Any],
    ) -> ChatResult:
        last_exc: Exception | None = None
        for model in self._candidate_models():
            try:
                method = getattr(model, method_name)
                return method(messages, stop=stop, run_manager=run_manager, **kwargs)
            except Exception as exc:
                last_exc = exc
        raise RuntimeError("No chat models configured for fallback routing.") from last_exc


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
            config.model_dump(exclude_none=True),
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
    agent_route = _agent_model_route(config, agent_name)
    profile_name = agent_route.model or config.default_model
    profile = _model_profile(config, profile_name, agent_name)
    fallback_profile_name = (
        agent_route.multimodal_fallback_model or config.default_multimodal_model
    )
    fallback_profile = (
        _model_profile(config, fallback_profile_name, agent_name, fallback=True)
        if fallback_profile_name
        else None
    )

    return ResolvedModelRoute(
        agent_name=agent_name,
        profile_name=profile_name,
        model=profile.model,
        base_url=profile.base_url,
        api_key_env=profile.api_key_env,
        api_key_present=bool(_api_key_from_env(profile).strip()),
        max_tokens=profile.max_tokens,
        thinking=profile.thinking,
        reasoning_effort=profile.reasoning_effort,
        multimodal_fallback_profile_name=fallback_profile_name,
        multimodal_fallback_model=(
            fallback_profile.model if fallback_profile is not None else None
        ),
        multimodal_fallback_base_url=(
            fallback_profile.base_url if fallback_profile is not None else None
        ),
        multimodal_fallback_api_key_env=(
            fallback_profile.api_key_env if fallback_profile is not None else None
        ),
        multimodal_fallback_api_key_present=(
            bool(_api_key_from_env(fallback_profile).strip())
            if fallback_profile is not None
            else False
        ),
        multimodal_fallback_max_tokens=(
            fallback_profile.max_tokens if fallback_profile is not None else None
        ),
        multimodal_fallback_thinking=(
            fallback_profile.thinking if fallback_profile is not None else None
        ),
        multimodal_fallback_reasoning_effort=(
            fallback_profile.reasoning_effort if fallback_profile is not None else None
        ),
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
    cfg = load_model_routing(workspace_root)
    route = resolve_model_route(workspace_root, agent_name, cfg)
    profile = cfg.models[route.profile_name]
    model = _build_chat_model_for_profile(
        workspace_root,
        agent_name,
        route.profile_name,
        profile,
        timeout=timeout,
    )
    fallback_profile_name = route.multimodal_fallback_profile_name
    if not fallback_profile_name or fallback_profile_name == route.profile_name:
        return model

    fallback_profile = cfg.models[fallback_profile_name]
    fallback_model = _build_chat_model_for_profile(
        workspace_root,
        agent_name,
        fallback_profile_name,
        fallback_profile,
        timeout=timeout,
        purpose="multimodal fallback",
    )
    return ChatModelWithFallbacks(primary=model, fallbacks=(fallback_model,))


def _build_chat_model_for_profile(
    workspace_root: str | Path,
    agent_name: str,
    profile_name: str,
    profile: ModelProfile,
    *,
    timeout: int,
    purpose: str = "primary",
):
    api_key_env = profile.api_key_env.strip()
    if not api_key_env:
        raise ValueError(
            f"Missing api_key_env for {purpose} model profile '{profile_name}'. "
            f"Set models.{profile_name}.api_key_env in "
            f"{model_routing_path(workspace_root)}."
        )
    api_key = _api_key_from_env(profile).strip()
    if not api_key:
        raise ValueError(
            f"Missing {purpose} model API key for agent '{agent_name}'. "
            f"Set {api_key_env} in the workspace .env or process environment."
        )

    from langchain_openai import ChatOpenAI
    import httpx

    base_url = normalize_openai_compatible_base_url(profile.base_url)
    parsed_base_url = urlparse(base_url)
    if not is_allowed_model_gateway(parsed_base_url):
        raise ValueError(
            "model base_url must be an HTTPS OpenAI-compatible gateway, "
            "or a local HTTP gateway on localhost/127.0.0.1."
        )

    model_kwargs: dict[str, Any] = {
        "model": profile.model,
        "base_url": base_url,
        "api_key": api_key,
        "max_tokens": profile.max_tokens,
        "streaming": False,
        "max_retries": 3,
        "timeout": timeout,
    }
    extra_body: dict[str, Any] = {}
    if profile.reasoning_effort is not None:
        extra_body["reasoning_effort"] = profile.reasoning_effort
    gateway_host = parsed_base_url.netloc.lower()
    if gateway_host == "api.deepseek.com":
        thinking = profile.thinking
        if thinking == "auto" and profile.model.startswith("deepseek-v4"):
            thinking = "disabled"
        if thinking in {"enabled", "disabled"}:
            extra_body["thinking"] = {"type": thinking}
    elif (
        gateway_host == "dashscope.aliyuncs.com"
        and profile.model.lower().startswith(("glm-", "zhipu/glm-"))
    ):
        if profile.thinking in {"enabled", "disabled"}:
            extra_body["enable_thinking"] = profile.thinking == "enabled"
    elif gateway_host.endswith(".volces.com"):
        if profile.thinking in {"enabled", "disabled"}:
            extra_body["thinking"] = {"type": profile.thinking}
    if extra_body:
        model_kwargs["extra_body"] = extra_body

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
        agent_route = _coerce_agent_model_route(profile_name)
        primary_profile_name = agent_route.model
        if primary_profile_name and primary_profile_name not in config.models:
            errors.append(
                f"Agent '{agent_name}' references unknown model profile "
                f"'{primary_profile_name}'."
            )
        fallback_profile_name = agent_route.multimodal_fallback_model
        if fallback_profile_name and fallback_profile_name not in config.models:
            errors.append(
                f"Agent '{agent_name}' references unknown multimodal fallback "
                f"model profile '{fallback_profile_name}'."
            )
    if config.default_model not in config.models:
        errors.append(
            f"default_model references unknown profile '{config.default_model}'."
        )
    if (
        config.default_multimodal_model
        and config.default_multimodal_model not in config.models
    ):
        errors.append(
            "default_multimodal_model references unknown profile "
            f"'{config.default_multimodal_model}'."
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
    if cfg.default_multimodal_model and cfg.default_multimodal_model not in cfg.models:
        raise ValueError(
            "default_multimodal_model references unknown profile "
            f"'{cfg.default_multimodal_model}'."
        )
    unknown: set[str] = set()
    for raw_route in cfg.agent_models.values():
        route = _coerce_agent_model_route(raw_route)
        for profile_name in (route.model, route.multimodal_fallback_model):
            if profile_name and profile_name not in cfg.models:
                unknown.add(profile_name)
    if unknown:
        raise ValueError("Unknown model profile(s): " + ", ".join(sorted(unknown)))


def _agent_model_route(config: ModelRoutingConfig, agent_name: str) -> AgentModelRoute:
    return _coerce_agent_model_route(config.agent_models.get(agent_name))


def _coerce_agent_model_route(raw_route: str | AgentModelRoute | None) -> AgentModelRoute:
    if raw_route is None:
        return AgentModelRoute()
    if isinstance(raw_route, AgentModelRoute):
        return raw_route
    return AgentModelRoute(model=raw_route)


def _model_profile(
    config: ModelRoutingConfig,
    profile_name: str,
    agent_name: str,
    *,
    fallback: bool = False,
) -> ModelProfile:
    try:
        return config.models[profile_name]
    except KeyError as exc:
        label = "multimodal fallback model profile" if fallback else "model profile"
        raise KeyError(
            f"Agent '{agent_name}' references unknown {label} '{profile_name}'."
        ) from exc


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
