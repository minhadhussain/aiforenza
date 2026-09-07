from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi import status

from app.api.deps.auth import get_current_dashboard_user
from app.models.topups import CreateTopupRequest
from app.services.stripe_payments import create_checkout_session
from app.services.stripe_payments import handle_checkout_completed
from app.services.stripe_payments import list_user_topups
from app.services.stripe_payments import verify_webhook_signature


router = APIRouter()


@router.get("/topups")
async def get_topups(user: dict = Depends(get_current_dashboard_user)) -> dict:
    return {"data": await list_user_topups(user["id"])}


@router.post("/topups/checkout", status_code=status.HTTP_201_CREATED)
async def post_topup_checkout(payload: CreateTopupRequest, user: dict = Depends(get_current_dashboard_user)) -> dict:
    result = await create_checkout_session(
        user_id=user["id"],
        email=user["email"],
        amount_cents=payload.amount_cents,
    )
    return {
        "checkout_url": result.checkout_url,
        "session_id": result.session_id,
        "amount_cents": result.amount_cents,
        "currency": result.currency,
    }


@router.post("/stripe/webhook")
async def post_stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict:
    payload = await request.body()
    event = verify_webhook_signature(payload, stripe_signature)

    if event.type == "checkout.session.completed":
        result = await handle_checkout_completed(event)
        return {
            "received": True,
            "processed": not result.already_processed,
            "already_processed": result.already_processed,
            "topup_id": result.topup_id,
        }

    return {"received": True, "ignored": True, "event_type": event.type}
