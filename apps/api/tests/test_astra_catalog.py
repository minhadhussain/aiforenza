import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from app.api.deps.api_keys import get_current_api_key
from app.api.deps.auth import get_current_dashboard_user
from app.api.routes import account
from app.main import app
from app.repositories import models as registry
from app.services.chat_completions import build_provider_payload
from app.models.openai import ChatCompletionRequest
from test_pricing import build_model


def catalog_row(slug):
    model = build_model()
    model.slug = slug
    model.display_name = slug
    model.provider = "azure"
    model.provider_model_id = slug
    model.enabled = model.pricing_verified = True
    model.reference_price_source = "fixture-reference"
    model.reference_price_valid_until = datetime.now(timezone.utc) + timedelta(days=1)
    return model.model_dump(mode="json")


def test_public_and_dashboard_share_authoritative_astra_registry(monkeypatch):
    slugs = ["gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6"]
    rows = [catalog_row(slug) for slug in slugs]
    lookup = AsyncMock(return_value=rows)
    monkeypatch.setattr(registry, "rest_select", lookup)
    # Both production routes use this repository, with actual serializers.
    app.dependency_overrides[get_current_api_key] = lambda: {
        "id": "test-key",
        "user_id": "test-owner",
    }
    app.dependency_overrides[get_current_dashboard_user] = lambda: {"id": "test-owner"}
    try:
        client = TestClient(app)
        public = client.get("/v1/models")
        dashboard = client.get("/v1/dashboard/models")
        public_catalog = client.get("/v1/public/models")
        assert (
            public.status_code
            == dashboard.status_code
            == public_catalog.status_code
            == 200
        )
        assert [m["id"] for m in public.json()["data"]] == slugs
        assert [m["slug"] for m in dashboard.json()["data"]] == slugs
        assert [m["slug"] for m in public_catalog.json()["data"]] == slugs
        astra = next(m for m in dashboard.json()["data"] if m["slug"] == "gpt-6-astra")
        assert astra["provider"] == "azure"
        assert astra["customer_input_price_per_million"] is not None
        assert lookup.await_count == 3
        assert all(
            call.kwargs["params"]["enabled"] == "eq.true"
            for call in lookup.call_args_list
        )
    finally:
        app.dependency_overrides.clear()


def test_astra_routes_to_registry_model_and_keeps_existing_pricing(monkeypatch):
    row = catalog_row("gpt-6-astra")
    monkeypatch.setattr(registry, "rest_select", AsyncMock(return_value=[row]))
    model = asyncio.run(registry.fetch_model_by_slug("gpt-6-astra"))
    payload = build_provider_payload(
        ChatCompletionRequest(
            model="gpt-6-astra",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=32,
        ),
        model,
        "req_fixture",
    )
    assert payload["model"] == row["provider_model_id"] == "gpt-6-astra"
    assert payload["max_completion_tokens"] == 32
    assert "max_tokens" not in payload
    assert str(model.input_price_per_million) == row["input_price_per_million"]


def test_unverified_pricing_is_not_bypassed_to_force_model_visibility(monkeypatch):
    row = catalog_row("gpt-6-astra")
    row["pricing_verified"] = False
    monkeypatch.setattr(registry, "rest_select", AsyncMock(return_value=[row]))
    assert asyncio.run(registry.fetch_enabled_models()) == []
    assert asyncio.run(registry.fetch_model_by_slug("gpt-6-astra")) is None
