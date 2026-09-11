import importlib
from pathlib import Path

import pytest


@pytest.fixture
def tool(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("configure_opencode_global")


def provider():
    return {
        "npm": "@ai-sdk/openai-compatible",
        "options": {"baseURL": "http://localhost:8000/v1", "apiKey": "PRIVATE_FIXTURE"},
        "models": {
            "gpt-5.4": {},
            "gpt-6-astra": {"options": {"reasoningEffort": "none"}},
        },
    }


def test_user_scope_merge_preserves_other_providers_and_defaults(tool):
    existing = {
        "model": "other/model",
        "small_model": "other/small",
        "permission": {"edit": "ask"},
        "enabled_providers": ["other"],
        "provider": {"other": {"models": {"model": {}}}},
    }
    merged = tool.merge_provider(existing, provider())
    assert merged["provider"]["other"] == existing["provider"]["other"]
    assert merged["model"] == "other/model" and merged["small_model"] == "other/small"
    assert merged["permission"] == existing["permission"]
    assert merged["enabled_providers"] == ["other", "aiforenza"]
    assert merged["provider"]["aiforenza"]["options"]["apiKey"] == "PRIVATE_FIXTURE"
    assert "aiforenza" not in existing["provider"]
    assert tool.merge_provider(merged, provider()) == merged


def test_existing_models_are_not_removed(tool):
    existing = {
        "provider": {"aiforenza": {"models": {"custom-model": {"name": "Custom"}}}}
    }
    assert (
        "custom-model"
        in tool.merge_provider(existing, provider())["provider"]["aiforenza"]["models"]
    )


@pytest.mark.parametrize(
    "config",
    [
        {"disabled_providers": ["aiforenza"]},
        {"provider": {"aiforenza": {"options": {"apiKey": "DIFFERENT_ACCOUNT"}}}},
        {
            "provider": {
                "aiforenza": {"options": {"baseURL": "https://another.invalid/v1"}}
            }
        },
    ],
)
def test_no_silent_key_or_policy_override(tool, config):
    with pytest.raises(RuntimeError):
        tool.merge_provider(config, provider())
