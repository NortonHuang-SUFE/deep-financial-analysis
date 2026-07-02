from __future__ import annotations

import pytest

from financial_agent_runtime.model_routing import (
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
        },
        "agent_models": {
            "morning_note": "qwen",
            "financial_facts_modeler": "deepseek",
        },
    }


def test_resolve_model_route_uses_agent_override_and_default(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_DEEPSEEK_API_KEY", "secret")
    save_model_routing(tmp_path, _routing_payload())

    overridden = resolve_model_route(tmp_path, "financial_facts_modeler")
    fallback = resolve_model_route(tmp_path, "unknown_agent")

    assert overridden.profile_name == "deepseek"
    assert overridden.model == "deepseek-chat"
    assert overridden.max_tokens == 8000
    assert overridden.api_key_present is True
    assert fallback.profile_name == "qwen"


def test_save_and_load_model_routing_round_trips(tmp_path):
    path = save_model_routing(tmp_path, ModelRoutingConfig(**_routing_payload()))
    cfg = load_model_routing(tmp_path)

    assert path.name == "model-routing.yaml"
    assert cfg.default_model == "qwen"
    assert set(cfg.models) == {"qwen", "deepseek"}
    assert cfg.agent_models["financial_facts_modeler"] == "deepseek"


def test_validate_model_routing_reports_unknown_profiles(tmp_path):
    payload = _routing_payload()
    payload["agent_models"]["bad_agent"] = "missing"

    cfg = ModelRoutingConfig(**payload)
    errors = validate_model_routing(tmp_path, cfg)

    assert errors == [
        "Agent 'bad_agent' references unknown model profile 'missing'."
    ]


def test_build_chat_model_for_agent_requires_profile_env_key(monkeypatch, tmp_path):
    monkeypatch.delenv("TEST_QWEN_API_KEY", raising=False)
    save_model_routing(tmp_path, _routing_payload())

    with pytest.raises(ValueError, match="TEST_QWEN_API_KEY"):
        build_chat_model_for_agent(tmp_path, "morning_note")


def test_explain_model_routes_does_not_expose_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_QWEN_API_KEY", "secret")
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
        }
    ]
