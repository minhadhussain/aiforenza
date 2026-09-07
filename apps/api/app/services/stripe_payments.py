from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import status

from app.core.config import settings
from app.core.errors import OpenAIAPIError
from app.models.topups import TopupResult
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.topups import complete_topup as complete_topup_record
from app.repositories.topups import create_pending_topup
from app.repositories.topups import fetch_topups


ALLOWED_TOPUP_AMOUNTS = {1000, 2500, 5000, 10000, 50000, 100000}


@dataclass
class CheckoutSessionResult:
    checkout_url: str
    session_id: str
    amount_cents: int
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
    return stripe.StripeClient(settings.stripe_secret_key)


def validate_topup_amount(amount_cents: int) -> None:
    if amount_cents not in ALLOWED_TOPUP_AMOUNTS:
        raise OpenAIAPIError(
            "Unsupported top-up amount.",
            error_type="invalid_request_error",
            code="invalid_topup_amount",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


async def create_checkout_session(*, user_id: str, email: str, amount_cents: int) -> CheckoutSessionResult:
    validate_topup_amount(amount_cents)
    client = _stripe_client()
    success_url = f"{settings.next_public_app_url.rstrip('/')}/dashboard?topup=success"
    cancel_url = f"{settings.next_public_app_url.rstrip('/')}/dashboard?topup=cancelled"

    session = client.checkout.sessions.create(
        {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "customer_email": email,
            "client_reference_id": user_id,
            "metadata": {
                "user_id": user_id,
                "amount_cents": str(amount_cents),
            },
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": "Wallet top-up",
                            "description": f"Prepaid API balance top-up of ${amount_cents / 100:.2f}",
                        },
                    },
                }
            ],
        }
    )

    try:
        await create_pending_topup(
            user_id=user_id,
            stripe_checkout_session_id=session.id,
            stripe_payment_intent_id=session.payment_intent if isinstance(session.payment_intent, str) else None,
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

    return CheckoutSessionResult(
        checkout_url=session.url,
        session_id=session.id,
        amount_cents=amount_cents,
        currency="USD",
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
        return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
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
    user_id = data.get("client_reference_id") or data.get("metadata", {}).get("user_id")
    amount_total = data.get("amount_total")
    currency = (data.get("currency") or "usd").upper()
    session_id = data.get("id")
    payment_intent_id = data.get("payment_intent")

    if not user_id or not amount_total or not session_id:
        raise OpenAIAPIError(
            "Stripe event is missing required data.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = await complete_topup_record(
            stripe_event_id=event.id,
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=payment_intent_id if isinstance(payment_intent_id, str) else None,
            user_id=user_id,
            amount_cents=int(amount_total),
            currency=currency,
        )
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="topup_complete_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

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
