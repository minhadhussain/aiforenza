import copy
import importlib
from pathlib import Path

import pytest

from app.models.catalog import CatalogModel
from app.services.opencode_config import build_opencode_config
from test_astra_catalog import catalog_row


@pytest.fixture
def refresh(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("refresh_opencode_configs")


def test_refresh_fixes_all_gpt_variants_without_changing_account_or_defaults(refresh):
    current = {"model": "other/model", "provider": {"other": {"options": {"apiKey": "OTHER_PRIVATE"}}, "aiforenza": {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": "http://localhost:8000/v1", "apiKey": "PRIVATE", "timeout": False}, "models": {"gpt-6-astra": {"reasoning": False, "options": {"reasoningEffort": "none"}}, "gpt-5.4": {"options": {"reasoningEffort": "high"}, "limit": {"output": 1024}}}}}}
    before = copy.deepcopy(current)
    downloaded = build_opencode_config([CatalogModel.model_validate(catalog_row(slug)) for slug in ("gpt-5.4", "gpt-5.6-sol", "gpt-6-astra")], "http://localhost:8000/v1")
    result = refresh.merge_config(current, downloaded)
    assert current == before
    assert result["model"] == "other/model" and result["provider"]["other"] == before["provider"]["other"]
    provider = result["provider"]["aiforenza"]
    assert provider["options"]["apiKey"] == "PRIVATE" and provider["options"]["timeout"] is False
    assert provider["models"]["gpt-5.4"]["options"]["reasoningEffort"] == "high"
    assert provider["models"]["gpt-5.4"]["limit"]["output"] == 1024
    assert provider["models"]["gpt-6-astra"]["options"]["reasoningEffort"] == "medium"
    assert all(model["reasoning"] for model in provider["models"].values())
    assert "max" not in provider["models"]["gpt-5.4"]["variants"]
    assert "max" in provider["models"]["gpt-5.6-sol"]["variants"]
    assert "none" not in provider["models"]["gpt-6-astra"]["variants"]
