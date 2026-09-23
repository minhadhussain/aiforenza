import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.catalog import CatalogModel
from app.repositories import models as registry
from app.api.routes import public_models
from app.services.models import ModelCatalogError
from app.services.opencode_config import build_opencode_config, model_entry, validate_api_base_url
from test_astra_catalog import catalog_row


def models():
    return [CatalogModel.model_validate(catalog_row(slug)) for slug in ("gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6")]


def test_config_uses_native_credential_store_and_exact_registry_variants():
    catalog = models()
    result = build_opencode_config(catalog, "https://api.example.com/v1/")
    provider = result["provider"]["aiforenza"]
    assert provider["options"] == {"baseURL": "https://api.example.com/v1", "timeout": 900000, "chunkTimeout": 900000}
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert set(provider["models"]) == {m.slug for m in catalog}
    astra = provider["models"]["gpt-6-astra"]
    assert list(astra["variants"]) == ["low", "medium", "high", "xhigh", "max"]
    assert astra["variants"] == {effort: {"reasoningEffort": effort} for effort in catalog[2].capabilities.reasoning_efforts}
    assert astra["options"] == {"reasoningEffort": "medium"}
    assert astra["reasoning"] and not astra["temperature"]
    assert astra["limit"] == {"context": 128000, "input": 90000, "output": 32000}
    assert result["model"] == result["small_model"] == "aiforenza/gpt-5.4"
    assert "apiKey" not in json.dumps(result) and "{env:" not in json.dumps(result)
    gpt54 = provider["models"]["gpt-5.4"]
    sol = provider["models"]["gpt-5.6-sol"]
    assert gpt54["reasoning"] and sol["reasoning"]
    assert list(gpt54["variants"]) == ["none", "low", "medium", "high", "xhigh"]
    assert list(sol["variants"]) == ["none", "low", "medium", "high", "xhigh", "max"]
    assert gpt54["options"]["reasoningEffort"] == "none"
    assert sol["options"]["reasoningEffort"] == "medium"


def test_config_defaults_to_an_available_model_and_handles_registry_changes():
    model = models()[2]
    model.slug = "fixture-reasoning-model"
    model.capabilities.reasoning_efforts = ["low", "high"]
    model.capabilities.default_reasoning_effort = "low"
    result = build_opencode_config([model], "http://localhost:8000/v1")
    assert result["model"] == "aiforenza/fixture-reasoning-model"
    assert set(result["provider"]["aiforenza"]["models"][model.slug]["variants"]) == {"low", "high"}
    model.capabilities.default_reasoning_effort = "none"
    with pytest.raises(ValueError):
        build_opencode_config([model], "http://localhost:8000/v1")
    with pytest.raises(ValueError):
        build_opencode_config([], "http://localhost:8000/v1")


def test_smaller_pricing_limits_bound_customer_configuration():
    model = models()[2]
    model.pricing_max_input_tokens = 20000
    model.pricing_max_output_tokens = 1000
    entry = model_entry(model)
    assert entry["limit"]["output"] == 1000
    assert entry["limit"]["input"] < model.pricing_max_input_tokens
    assert entry["limit"]["context"] <= 21000


@pytest.mark.parametrize("url", ["https://api.example.com/v1", "https://api.example.com/ai/v1/", "http://localhost:8000/v1", "http://127.0.0.1:8000/v1", "http://[::1]:8000/v1"])
def test_valid_configured_endpoints(url):
    assert validate_api_base_url(url) == url.rstrip("/")


@pytest.mark.parametrize("url", ["", "javascript:alert(1)", "https://api.example.com", "http://api.example.com/v1", "https://user:PRIVATE@example.com/v1", "https://api.example.com/v1?key=PRIVATE", "https://api.example.com/v1#key", "https://api.example.com:99999/v1", "https://api.example.com/\\v1"])
def test_invalid_or_credential_bearing_endpoints_rejected(url):
    with pytest.raises(ValueError):
        validate_api_base_url(url)


@pytest.mark.parametrize("url", ["http://localhost:8000/v1", "https://localhost/v1", "http://127.0.0.1:8000/v1", "https://0.0.0.0/v1"])
def test_production_does_not_give_remote_customers_a_loopback_config(url):
    with pytest.raises(ValueError):
        validate_api_base_url(url, production=True)


def test_public_download_is_authoritative_and_cannot_be_redirected_by_request(monkeypatch):
    rows = [catalog_row(slug) for slug in ("gpt-5.4", "gpt-6-astra", "disabled-model", "unpriced-model")]
    rows[0]["provider_model_id"] = "PRIVATE_DEPLOYMENT"
    rows[2]["enabled"] = False
    rows[3]["pricing_verified"] = False
    monkeypatch.setattr(registry, "rest_select", AsyncMock(return_value=rows))
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com/v1")
    monkeypatch.setattr(settings, "api_env", "production")
    monkeypatch.setattr(settings, "azure_api_key", "PRIVATE_AZURE_KEY")
    response = TestClient(app).get("/v1/public/opencode-config?base_url=https://evil.invalid/v1&api_key=PRIVATE_CLIENT_KEY", headers={"Host": "evil.invalid"})
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="opencode.json"'
    assert response.headers["cache-control"] == "no-store"
    provider = response.json()["provider"]["aiforenza"]
    assert set(provider["models"]) == {"gpt-5.4", "gpt-6-astra"}
    assert provider["options"]["baseURL"] == "https://api.example.com/v1"
    assert "PRIVATE" not in response.text and "evil.invalid" not in response.text


def test_unavailable_registry_does_not_download_stale_or_empty_models(monkeypatch):
    monkeypatch.setattr(public_models, "list_models", AsyncMock(side_effect=ModelCatalogError("PRIVATE_DETAILS")))
    response = TestClient(app).get("/v1/public/opencode-config")
    assert response.status_code == 503 and "PRIVATE" not in response.text


def test_production_configuration_error_is_safe(monkeypatch):
    monkeypatch.setattr(public_models, "list_models", AsyncMock(return_value=models()))
    monkeypatch.setattr(settings, "public_api_base_url", "http://localhost:8000/v1")
    monkeypatch.setattr(settings, "api_env", "production")
    assert TestClient(app).get("/v1/public/opencode-config").status_code == 503
