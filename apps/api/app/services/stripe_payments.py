from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import status

from app.core.config import settings
from app.core.errors import OpenAIAPIError
from app.models.topups import CreateTopupRequest
from app.models.topups import TopupResult
from app.models.topups import resolve_package_value_usd_cents
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.topups import attach_checkout_session_to_topup
from app.repositories.topups import complete_topup as complete_topup_record
from app.repositories.topups import create_pending_topup
from app.repositories.topups import fetch_topup_by_id
from app.repositories.topups import fetch_topups
from app.services.fx_rates import get_usd_inr_quote
from app.services.fx_rates import usd_cents_to_inr_minor_units
from app.services.observability import capture_event


ALLOWED_TOPUP_AMOUNTS = {1000, 2500, 5000, 10000, 50000, 100000}


@dataclass
class CheckoutSessionResult:
    checkout_url: str
    session_id: str
    package_id: str
    package_value_usd_cents: int
    stripe_amount_inr: int
    currency: str


def _stripe_client() -> stripe.StripeClient:
    import stripe

    if not settings.stripe_secret_key:
        raise OpenAIAPIError(
            "Stripe is not configured.",
            error_type="api_error",
            code="stripe_not_configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if settings.api_env != "production" and not settings.stripe_secret_key.startswith(
        "sk_test_"
    ):
        raise OpenAIAPIError(
            "Local payments require a Stripe test key.",
            error_type="api_error",
            code="stripe_test_mode_required",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return stripe.StripeClient(settings.stripe_secret_key)


def _stripe_error_message(exc: Exception) -> str:
    message = (
        getattr(exc, "user_message", None) or getattr(exc, "message", None) or str(exc)
    )
    return str(message)


def validate_topup_amount(amount_cents: int) -> None:
    if amount_cents not in ALLOWED_TOPUP_AMOUNTS:
        raise OpenAIAPIError(
            "Unsupported top-up amount.",
            error_type="invalid_request_error",
            code="invalid_topup_amount",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def resolve_package(package_id: str) -> int:
    try:
        amount_cents = resolve_package_value_usd_cents(package_id)
    except ValueError as exc:
        raise OpenAIAPIError(
            "Unsupported top-up package.",
            error_type="invalid_request_error",
            code="invalid_topup_amount",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
    validate_topup_amount(amount_cents)
    return amount_cents


async def create_checkout_session(
    *, user_id: str, email: str, package_id: str
) -> CheckoutSessionResult:
    amount_cents = resolve_package(package_id)
    client = _stripe_client()
    success_url = f"{settings.next_public_app_url.rstrip('/')}/dashboard/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = (
        f"{settings.next_public_app_url.rstrip('/')}/dashboard/billing?cancelled=true"
    )
    stripe_currency = settings.stripe_domestic_currency.lower()

    if stripe_currency != "inr":
        raise OpenAIAPIError(
            "Only domestic INR Stripe payments are supported.",
            error_type="api_error",
            code="stripe_domestic_only",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    quote = await get_usd_inr_quote()
    stripe_amount_inr = usd_cents_to_inr_minor_units(amount_cents, quote)

    try:
        topup = await create_pending_topup(
            user_id=user_id,
            package_id=package_id,
            package_value_usd_cents=amount_cents,
            stripe_amount_inr=stripe_amount_inr,
            stripe_currency=stripe_currency.upper(),
            exchange_rate_used=quote.rate,
            stripe_checkout_session_id=f"pending:{uuid4()}",
            stripe_payment_intent_id=None,
            amount_cents=amount_cents,
            currency="USD",
        )
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="topup_create_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    try:
        session = client.checkout.sessions.create(
            {
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "customer_email": email,
                "client_reference_id": user_id,
                "metadata": {
                    "user_id": user_id,
                    "topup_id": topup["id"],
                    "package_id": package_id,
                    "package_value_usd_cents": str(amount_cents),
                    "stripe_amount_inr": str(stripe_amount_inr),
                },
                "line_items": [
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": stripe_currency,
                            "unit_amount": stripe_amount_inr,
                            "product_data": {
                                "name": "Wallet top-up",
                                "description": f"Prepaid AI Forenza balance top-up worth ${amount_cents / 100:.2f} billed in INR",
                            },
                        },
                    }
                ],
            }
        )
    except Exception as exc:
        raise OpenAIAPIError(
            _stripe_error_message(exc),
            error_type="api_error",
            code="stripe_checkout_failed",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    try:
        await attach_checkout_session_to_topup(
            topup_id=topup["id"],
            stripe_checkout_session_id=session.id,
            stripe_payment_intent_id=session.payment_intent
            if isinstance(session.payment_intent, str)
            else None,
        )
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="topup_create_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    capture_event(
        user_id,
        "topup_started",
        {
            "topup_id": topup["id"],
            "package_id": package_id,
            "package_value_usd_cents": amount_cents,
            "stripe_amount_inr": stripe_amount_inr,
            "fx_source": quote.source,
        },
    )

    return CheckoutSessionResult(
        checkout_url=session.url,
        session_id=session.id,
        package_id=package_id,
        package_value_usd_cents=amount_cents,
        stripe_amount_inr=stripe_amount_inr,
        currency=stripe_currency.upper(),
    )


def verify_webhook_signature(payload: bytes, signature: str | None) -> Any:
    import stripe

    if not settings.stripe_webhook_secret:
        raise OpenAIAPIError(
            "Stripe webhook secret is not configured.",
            error_type="api_error",
            code="stripe_not_configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if not signature:
        raise OpenAIAPIError(
            "Missing Stripe signature.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        return stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError as exc:
        raise OpenAIAPIError(
            "Invalid Stripe signature.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
    except ValueError as exc:
        raise OpenAIAPIError(
            "Invalid webhook payload.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc


async def handle_checkout_completed(event: Any) -> TopupResult:
    data = event.data["object"]
    if (
        data.get("mode") != "payment"
        or data.get("payment_status") != "paid"
        or data.get("status") != "complete"
    ):
        raise OpenAIAPIError(
            "Checkout payment is not confirmed.",
            error_type="invalid_request_error",
            code="payment_not_paid",
            status_code=400,
        )
    if settings.api_env != "production" and data.get("livemode") is not False:
        raise OpenAIAPIError(
            "Live payments are disabled locally.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=400,
        )

    user_id = data.get("client_reference_id") or data.get("metadata", {}).get("user_id")
    topup_id = data.get("metadata", {}).get("topup_id")
    package_id = data.get("metadata", {}).get("package_id")
    package_value_usd_cents = data.get("metadata", {}).get("package_value_usd_cents")
    stripe_amount_inr = data.get("metadata", {}).get("stripe_amount_inr")
    amount_total = data.get("amount_total")
    currency = (data.get("currency") or "").upper()
    session_id = data.get("id")
    payment_intent_id = data.get("payment_intent")

    if (
        not user_id
        or not amount_total
        or not session_id
        or not topup_id
        or not package_id
        or not package_value_usd_cents
        or not stripe_amount_inr
    ):
        raise OpenAIAPIError(
            "Stripe event is missing required data.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        topup = await fetch_topup_by_id(topup_id)
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="topup_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if topup is None:
        raise OpenAIAPIError(
            "Top-up record not found.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if topup["user_id"] != user_id:
        raise OpenAIAPIError(
            "Top-up does not belong to the expected user.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if (
        topup["stripe_checkout_session_id"] != session_id
        or topup["package_id"] != package_id
        or topup["package_value_usd_cents"] != int(package_value_usd_cents)
        or topup["stripe_amount_inr"] != int(stripe_amount_inr)
        or topup["stripe_currency"].upper() != "INR"
        or int(amount_total) != int(stripe_amount_inr)
        or currency != "INR"
        or topup["currency"].upper() != "USD"
    ):
        raise OpenAIAPIError(
            "Checkout does not match the top-up.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=400,
        )

    try:
        payload = await complete_topup_record(
            stripe_event_id=event.id,
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=payment_intent_id
            if isinstance(payment_intent_id, str)
            else None,
            user_id=user_id,
            amount_cents=int(package_value_usd_cents),
            currency="USD",
        )
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="topup_complete_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    capture_event(
        user_id,
        "topup_completed",
        {
            "topup_id": topup_id,
            "package_id": package_id,
            "package_value_usd_cents": int(package_value_usd_cents),
            "stripe_amount_inr": int(stripe_amount_inr),
        },
    )

    return TopupResult.model_validate(payload)


async def list_user_topups(user_id: str) -> list[dict]:
    try:
        return await fetch_topups(user_id)
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="topup_list_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
