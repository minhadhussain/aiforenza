import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import OpenAIAPIError
from app.services import fx_rates
from app.services.fx_rates import FxQuote, usd_cents_to_inr_minor_units


def test_usd_cents_to_inr_minor_units_uses_configured_rate():
    quote = FxQuote(pair="USD/INR", rate="95.12", source="test")
    assert usd_cents_to_inr_minor_units(1000, quote) == 95120


def test_cached_valid_rate_is_reused(monkeypatch):
    class FakeRedis:
        def get(self, key):
            return '{"pair":"USD/INR","rate":"95.12","source":"cache"}'

    monkeypatch.setattr(fx_rates, "_client", lambda: FakeRedis())
    quote = asyncio.run(fx_rates.get_usd_inr_quote())
    assert quote.rate == "95.12"
    assert quote.source == "cache"


def test_invalid_remote_rate_fails_safely(monkeypatch):
    class FakeRedis:
        def get(self, key):
            return None

    class BadResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"rates": {"INR": 0}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            return BadResponse()

    monkeypatch.setattr(fx_rates, "_client", lambda: FakeRedis())
    monkeypatch.setattr(fx_rates.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(settings, "stripe_fx_rate_api_url", "https://frankfurter.test")
    with pytest.raises(OpenAIAPIError) as error:
        asyncio.run(fx_rates.get_usd_inr_quote())
    assert error.value.code == "fx_rate_unavailable"


def test_redis_failure_can_use_existing_cached_value(monkeypatch):
    class BrokenRedis:
        def get(self, key):
            raise RedisError("redis down")

        def setex(self, *args, **kwargs):
            raise RedisError("redis down")

    class GoodResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"rates": {"INR": 95.12}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            return GoodResponse()

    monkeypatch.setattr(fx_rates, "_client", lambda: BrokenRedis())
    monkeypatch.setattr(fx_rates.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(settings, "stripe_fx_rate_api_url", "https://frankfurter.test")
    quote = asyncio.run(fx_rates.get_usd_inr_quote())
    assert quote.rate == "95.12"
