from __future__ import annotations

import pytest
from deepagents._models import resolve_model as resolve_deepagents_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from financial_agent_runtime.model_routing import (
    ChatModelWithFallbacks,
    ModelRoutingConfig,
    build_chat_model_for_agent,
    explain_model_routes,
    load_model_routing,
    resolve_model_route,
    save_model_routing,
    validate_model_routing,
)


def _routing_payload() -> dict:
    return {
        "default_model": "qwen",
        "default_multimodal_model": "qwen-vl",
        "models": {
            "qwen": {
                "model": "qwen-3.7-max",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
                "api_key_env": "TEST_QWEN_API_KEY",
                "max_tokens": 16000,
                "thinking": "auto",
            },
            "deepseek": {
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "api_key_env": "TEST_DEEPSEEK_API_KEY",
                "max_tokens": 8000,
                "thinking": "disabled",
            },
            "qwen-vl": {
                "model": "qwen-vl-max",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
                "api_key_env": "TEST_QWEN_VL_API_KEY",
                "max_tokens": 12000,
                "thinking": "auto",
            },
        },
        "agent_models": {
            "morning_note": {
                "model": "qwen",
                "multimodal_fallback_model": "qwen-vl",
            },
            "html_image_renderer": {
                "model": "deepseek",
                "multimodal_fallback_model": "qwen-vl",
            },
        },
    }


def test_resolve_model_route_uses_agent_override_and_default(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_DEEPSEEK_API_KEY", "secret")
    save_model_routing(tmp_path, _routing_payload())

    overridden = resolve_model_route(tmp_path, "html_image_renderer")
    fallback = resolve_model_route(tmp_path, "unknown_agent")

    assert overridden.profile_name == "deepseek"
    assert overridden.model == "deepseek-chat"
    assert overridden.max_tokens == 8000
    assert overridden.api_key_present is True
    assert overridden.multimodal_fallback_profile_name == "qwen-vl"
    assert overridden.multimodal_fallback_model == "qwen-vl-max"
    assert fallback.profile_name == "qwen"
    assert fallback.multimodal_fallback_profile_name == "qwen-vl"


def test_save_and_load_model_routing_round_trips(tmp_path):
    path = save_model_routing(tmp_path, ModelRoutingConfig(**_routing_payload()))
    cfg = load_model_routing(tmp_path)

    assert path.name == "model-routing.yaml"
    assert cfg.default_model == "qwen"
    assert cfg.default_multimodal_model == "qwen-vl"
    assert set(cfg.models) == {"qwen", "deepseek", "qwen-vl"}
    assert cfg.agent_models["html_image_renderer"].model == "deepseek"
    assert (
        cfg.agent_models["html_image_renderer"].multimodal_fallback_model
        == "qwen-vl"
    )


def test_validate_model_routing_reports_unknown_profiles(tmp_path):
    payload = _routing_payload()
    payload["agent_models"]["bad_agent"] = "missing"

    cfg = ModelRoutingConfig(**payload)
    errors = validate_model_routing(tmp_path, cfg)

    assert errors == [
        "Agent 'bad_agent' references unknown model profile 'missing'."
    ]


def test_validate_model_routing_reports_unknown_fallback_profiles(tmp_path):
    payload = _routing_payload()
    payload["agent_models"]["bad_agent"] = {
        "model": "qwen",
        "multimodal_fallback_model": "missing-vision",
    }

    cfg = ModelRoutingConfig(**payload)
    errors = validate_model_routing(tmp_path, cfg)

    assert errors == [
        "Agent 'bad_agent' references unknown multimodal fallback model profile "
        "'missing-vision'."
    ]


def test_build_chat_model_for_agent_requires_profile_env_key(monkeypatch, tmp_path):
    monkeypatch.delenv("TEST_QWEN_API_KEY", raising=False)
    save_model_routing(tmp_path, _routing_payload())

    with pytest.raises(ValueError, match="TEST_QWEN_API_KEY"):
        build_chat_model_for_agent(tmp_path, "morning_note")


def test_build_chat_model_for_agent_requires_fallback_env_key(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_QWEN_API_KEY", "secret")
    monkeypatch.delenv("TEST_QWEN_VL_API_KEY", raising=False)
    save_model_routing(tmp_path, _routing_payload())

    with pytest.raises(ValueError, match="multimodal fallback model API key"):
        build_chat_model_for_agent(tmp_path, "morning_note")


def test_build_chat_model_for_agent_adds_multimodal_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_QWEN_API_KEY", "secret")
    monkeypatch.setenv("TEST_QWEN_VL_API_KEY", "vision-secret")
    save_model_routing(tmp_path, _routing_payload())

    model = build_chat_model_for_agent(tmp_path, "morning_note")

    assert isinstance(model, ChatModelWithFallbacks)
    assert isinstance(model, BaseChatModel)
    assert resolve_deepagents_model(model) is model
    assert model.primary.model_name == "qwen-3.7-max"
    assert len(model.fallbacks) == 1
    assert model.fallbacks[0].model_name == "qwen-vl-max"


def test_build_chat_model_for_agent_passes_reasoning_effort(monkeypatch, tmp_path):
    payload = _routing_payload()
    payload["models"]["kimi-k3"] = {
        "model": "kimi/kimi-k3",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "TEST_KIMI_API_KEY",
        "max_tokens": 131072,
        "thinking": "enabled",
        "reasoning_effort": "max",
    }
    payload["agent_models"]["kimi_agent"] = {
        "model": "kimi-k3",
        "multimodal_fallback_model": "kimi-k3",
    }
    monkeypatch.setenv("TEST_KIMI_API_KEY", "secret")
    save_model_routing(tmp_path, payload)

    model = build_chat_model_for_agent(tmp_path, "kimi_agent")

    assert model.model_name == "kimi/kimi-k3"
    assert model.max_tokens == 131072
    assert model.extra_body == {"reasoning_effort": "max"}
    request_payload = model._get_request_payload([HumanMessage(content="hello")])
    assert request_payload["max_completion_tokens"] == 131072
    assert request_payload["extra_body"] == {"reasoning_effort": "max"}


@pytest.mark.parametrize(
    ("profile_name", "model_name", "base_url", "expected_extra_body"),
    [
        (
            "aliyun-glm",
            "glm-5.2-fast-preview",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            {"enable_thinking": False},
        ),
        (
            "volcengine-glm",
            "glm-5-2-260617",
            "https://ark.cn-beijing.volces.com/api/v3",
            {"thinking": {"type": "disabled"}},
        ),
    ],
)
def test_build_chat_model_for_agent_disables_glm_thinking(
    monkeypatch,
    tmp_path,
    profile_name,
    model_name,
    base_url,
    expected_extra_body,
):
    payload = _routing_payload()
    payload["models"][profile_name] = {
        "model": model_name,
        "base_url": base_url,
        "api_key_env": "TEST_GLM_API_KEY",
        "max_tokens": 131072,
        "thinking": "disabled",
    }
    payload["agent_models"]["glm_agent"] = {
        "model": profile_name,
        "multimodal_fallback_model": profile_name,
    }
    monkeypatch.setenv("TEST_GLM_API_KEY", "secret")
    save_model_routing(tmp_path, payload)

    model = build_chat_model_for_agent(tmp_path, "glm_agent")

    assert model.model_name == model_name
    assert model.extra_body == expected_extra_body
    request_payload = model._get_request_payload([HumanMessage(content="hello")])
    assert request_payload["extra_body"] == expected_extra_body


def test_legacy_string_agent_model_binding_still_supported(tmp_path):
    payload = _routing_payload()
    payload["agent_models"]["legacy_agent"] = "deepseek"
    cfg = ModelRoutingConfig(**payload)

    route = resolve_model_route(tmp_path, "legacy_agent", cfg)

    assert route.profile_name == "deepseek"
    assert route.multimodal_fallback_profile_name == "qwen-vl"


def test_explain_model_routes_does_not_expose_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_QWEN_API_KEY", "secret")
    monkeypatch.setenv("TEST_QWEN_VL_API_KEY", "vision-secret")
    save_model_routing(tmp_path, _routing_payload())

    routes = explain_model_routes(tmp_path, ["morning_note"])

    assert routes == [
        {
            "agent_name": "morning_note",
            "profile_name": "qwen",
            "model": "qwen-3.7-max",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
            "api_key_env": "TEST_QWEN_API_KEY",
            "api_key_present": True,
            "max_tokens": 16000,
            "thinking": "auto",
            "reasoning_effort": None,
            "multimodal_fallback_profile_name": "qwen-vl",
            "multimodal_fallback_model": "qwen-vl-max",
            "multimodal_fallback_base_url": (
                "https://dashscope.aliyuncs.com/compatible-mode"
            ),
            "multimodal_fallback_api_key_env": "TEST_QWEN_VL_API_KEY",
            "multimodal_fallback_api_key_present": True,
            "multimodal_fallback_max_tokens": 12000,
            "multimodal_fallback_thinking": "auto",
            "multimodal_fallback_reasoning_effort": None,
        }
    ]
