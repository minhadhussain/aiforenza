import copy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.models.catalog import ModelCapabilities


@pytest.fixture
def sync(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("sync_opencode_models")


def test_merge_preserves_credentials_defaults_and_customizations(sync):
    config = {
        "model": "aiforenza/gpt-5.4",
        "small_model": "aiforenza/gpt-5.4",
        "provider": {
            "aiforenza": {
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": "http://localhost:8000/v1",
                    "apiKey": "PRIVATE_FIXTURE",
                },
                "models": {
                    "gpt-5.4": {
                        "limit": {"context": 64000, "output": 1024},
                        "options": {"custom": True},
                    }
                },
            }
        },
    }
    before = copy.deepcopy(config)
    models = [
        SimpleNamespace(
            slug=s,
            display_name=s,
            pricing_max_input_tokens=190000,
            pricing_max_output_tokens=32768,
            capabilities=ModelCapabilities(reasoning=s == "gpt-6-astra", reasoning_efforts=["low", "medium", "high", "xhigh", "max"], default_reasoning_effort="medium", context=128000, temperature=False),
        )
        for s in ("gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6")
    ]
    merged = sync.merged_config(config, models)
    assert config == before
    assert merged["model"] == before["model"]
    assert merged["small_model"] == before["small_model"]
    assert (
        merged["provider"]["aiforenza"]["options"]
        == before["provider"]["aiforenza"]["options"]
    )
    entries = merged["provider"]["aiforenza"]["models"]
    assert entries["gpt-5.4"]["limit"] == {
        "context": 64000,
        "output": 1024,
        "input": 62976,
    }
    assert entries["gpt-5.4"]["options"] == {"custom": True}
    assert entries["gpt-6-astra"]["limit"] == {
        "context": 128000,
        "output": 32000,
        "input": 90000,
    }
    assert merged["compaction"] == {"auto": True, "prune": True, "reserved": 16000}
    assert entries["gpt-6-astra"]["options"]["reasoningEffort"] == "medium"
    assert entries["gpt-6-astra"]["reasoning"] is True
    assert entries["gpt-6-astra"]["variants"] == {effort: {"reasoningEffort": effort} for effort in ("low", "medium", "high", "xhigh", "max")}
    assert "reasoning_effort" not in entries["gpt-6-astra"]["options"]
    assert sync.merged_config(merged, models) == merged


def test_template_contains_only_supported_models_and_no_literal_key():
    path = Path(__file__).resolve().parents[3] / "docs/opencode.example.json"
    config = json.loads(path.read_text())
    provider = config["provider"]["aiforenza"]
    assert set(provider["models"]) == {
        "gpt-5.4",
        "gpt-5.6-sol",
        "gpt-6-astra",
        "grok-4.6",
    }
    assert "apiKey" not in provider["options"]  # Credential comes from /connect.


def test_reasoning_timeouts_come_from_registry_and_preserve_unlimited_override(sync):
    config = {"provider": {"aiforenza": {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": "http://localhost:8000/v1", "apiKey": "PRIVATE_FIXTURE", "timeout": False}}}}
    from app.models.catalog import CatalogModel
    from test_astra_catalog import catalog_row

    result = sync.merged_config(config, [CatalogModel.model_validate(catalog_row("gpt-6-astra"))])
    options = result["provider"]["aiforenza"]["options"]
    assert options["timeout"] is False
    assert options["chunkTimeout"] == 900000
    assert options["apiKey"] == "PRIVATE_FIXTURE"
