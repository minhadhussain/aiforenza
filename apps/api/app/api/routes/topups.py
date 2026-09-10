from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi import status

from app.api.deps.auth import get_current_dashboard_user
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.wallets import bootstrap_user_account
from app.core.errors import OpenAIAPIError
from app.models.topups import CreateTopupRequest
from app.services.stripe_payments import create_checkout_session
from app.services.stripe_payments import handle_checkout_completed
from app.services.stripe_payments import list_user_topups
from app.services.stripe_payments import verify_webhook_signature


router = APIRouter()


@router.get("/topups")
async def get_topups(user: dict = Depends(get_current_dashboard_user)) -> dict:
    try:
        await bootstrap_user_account(user["id"], user["email"])
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="account_bootstrap_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return {"data": await list_user_topups(user["id"])}


@router.post("/topups/checkout", status_code=status.HTTP_201_CREATED)
async def post_topup_checkout(
    payload: CreateTopupRequest, user: dict = Depends(get_current_dashboard_user)
) -> dict:
    try:
        await bootstrap_user_account(user["id"], user["email"])
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="account_bootstrap_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    result = await create_checkout_session(
        user_id=user["id"],
        email=user["email"],
        package_id=payload.package_id,
    )
    return {
        "checkout_url": result.checkout_url,
        "session_id": result.session_id,
        "package_id": result.package_id,
        "package_value_usd_cents": result.package_value_usd_cents,
        "stripe_amount_inr": result.stripe_amount_inr,
        "currency": result.currency,
    }


@router.post("/billing/create-checkout-session", status_code=status.HTTP_201_CREATED)
async def post_billing_checkout(
    payload: CreateTopupRequest, user: dict = Depends(get_current_dashboard_user)
) -> dict:
    return await post_topup_checkout(payload, user)


@router.post("/stripe/webhook")
async def post_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    payload = await request.body()
    event = verify_webhook_signature(payload, stripe_signature)

    if event.type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        # Delayed payment methods complete Checkout before funds are confirmed.
        # Acknowledge the pending event; only the later paid event may credit.
        if (
            event.type == "checkout.session.completed"
            and event.data["object"].get("payment_status") == "unpaid"
        ):
            return {"received": True, "processed": False, "pending_payment": True}
        result = await handle_checkout_completed(event)
        return {
            "received": True,
            "processed": not result.already_processed,
            "already_processed": result.already_processed,
            "topup_id": result.topup_id,
        }

    return {"received": True, "ignored": True, "event_type": event.type}


@router.post("/webhooks/stripe")
async def post_stripe_webhook_local(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    return await post_stripe_webhook(request, stripe_signature)
