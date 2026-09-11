import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def inspect_tool(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("inspect_opencode_visibility")


def test_default_other_model_does_not_hide_astra(inspect_tool):
    config = {
        "model": "aiforenza/gpt-5.4",
        "small_model": "aiforenza/gpt-5.4",
        "provider": {
            "aiforenza": {
                "models": {"gpt-6-astra": {"name": "GPT-6 Astra", "reasoning": False}},
                "options": {
                    "apiKey": "PRIVATE_KEY",
                    "headers": {"Authorization": "PRIVATE_TOKEN"},
                },
            }
        },
    }
    result = inspect_tool.summary(config)
    assert result["provider_present"] and "gpt-6-astra" in result["model_ids"]
    assert not result["default_is_astra"] and not result["astra_blacklisted"]
    assert "PRIVATE" not in json.dumps(result)
    assert "headers" not in json.dumps(result)


def test_visibility_filters_reported_without_credentials(inspect_tool):
    result = inspect_tool.summary(
        {
            "enabled_providers": ["other"],
            "disabled_providers": ["aiforenza"],
            "provider": {
                "aiforenza": {"blacklist": ["gpt-6-astra"], "whitelist": ["gpt-5.4"]}
            },
        }
    )
    assert result["provider_disabled"] and result["astra_blacklisted"]
    assert (
        result["provider_allowlisted"] is False and result["astra_whitelisted"] is False
    )
