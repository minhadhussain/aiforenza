from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import httpx
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import OpenAIAPIError


FX_CACHE_KEY = "fx:usd_inr:quote"
FX_TTL_SECONDS = 3600


@dataclass(frozen=True)
class FxQuote:
    pair: str
    rate: str
    source: str


def _client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _parse_rate(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise ValueError("invalid_fx_payload")
    value = None
    if isinstance(payload.get("rates"), dict):
        value = payload["rates"].get("INR")
    if value is None and payload.get("base") == "USD" and payload.get("quote") == "INR":
        value = payload.get("rate")
    if value is None and payload.get("pair") == "USD/INR":
        value = payload.get("rate")
    rate = Decimal(str(value))
    if not rate.is_finite() or rate <= 0:
        raise ValueError("invalid_fx_rate")
    return str(rate)


def _cached_quote() -> FxQuote | None:
    try:
        raw = _client().get(FX_CACHE_KEY)
        if not raw:
            return None
        payload = json.loads(raw)
        if payload.get("pair") != "USD/INR":
            return None
        rate = _parse_rate(payload)
        return FxQuote(pair="USD/INR", rate=rate, source=payload.get("source", "cache"))
    except (RedisError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _store_quote(quote: FxQuote) -> None:
    try:
        _client().setex(
            FX_CACHE_KEY,
            FX_TTL_SECONDS,
            json.dumps(
                {"pair": quote.pair, "rate": quote.rate, "source": quote.source}
            ),
        )
    except RedisError:
        return


async def get_usd_inr_quote() -> FxQuote:
    cached = _cached_quote()
    if cached:
        return cached

    url = settings.stripe_fx_rate_api_url
    if not url:
        raise OpenAIAPIError(
            "FX rate source is not configured.",
            error_type="api_error",
            code="fx_rate_unavailable",
            status_code=503,
        )

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        rate = _parse_rate(payload)
        quote = FxQuote(pair="USD/INR", rate=rate, source=url)
        _store_quote(quote)
        return quote
    except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise OpenAIAPIError(
            "Unable to retrieve a valid USD/INR rate right now.",
            error_type="api_error",
            code="fx_rate_unavailable",
            status_code=503,
        ) from exc


def usd_cents_to_inr_minor_units(usd_cents: int, quote: FxQuote) -> int:
    value = (Decimal(usd_cents) / Decimal("100")) * Decimal(quote.rate) * Decimal("100")
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
