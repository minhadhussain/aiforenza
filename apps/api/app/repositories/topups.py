from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.supabase_rest import execute_rest_mutation
from app.repositories.supabase_rest import execute_rest_rpc
from app.repositories.supabase_rest import rest_select


async def create_pending_topup(
    *,
    user_id: str,
    package_id: str,
    package_value_usd_cents: int,
    stripe_amount_inr: int,
    stripe_currency: str,
    exchange_rate_used: str,
    stripe_checkout_session_id: str,
    stripe_payment_intent_id: str | None,
    amount_cents: int,
    currency: str,
) -> dict:
    response = await execute_rest_mutation(
        path="/rest/v1/topups",
        method="POST",
        json={
            "user_id": user_id,
            "package_id": package_id,
            "package_value_usd_cents": package_value_usd_cents,
            "stripe_amount_inr": stripe_amount_inr,
            "stripe_currency": stripe_currency,
            "exchange_rate_used": exchange_rate_used,
            "stripe_checkout_session_id": stripe_checkout_session_id,
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "amount_cents": amount_cents,
            "currency": currency,
            "status": "PENDING",
        },
        prefer="return=representation",
    )
    return response[0] if isinstance(response, list) else response


async def attach_checkout_session_to_topup(
    *,
    topup_id: str,
    stripe_checkout_session_id: str,
    stripe_payment_intent_id: str | None,
) -> dict:
    response = await execute_rest_mutation(
        path=f"/rest/v1/topups?id=eq.{topup_id}",
        method="PATCH",
        json={
            "stripe_checkout_session_id": stripe_checkout_session_id,
            "stripe_payment_intent_id": stripe_payment_intent_id,
        },
        prefer="return=representation",
    )
    return response[0] if isinstance(response, list) else response


async def fetch_topup_by_id(topup_id: str) -> dict | None:
    payload = await rest_select(
        path="/rest/v1/topups",
        params={
            "id": f"eq.{topup_id}",
            "select": "id,user_id,package_id,package_value_usd_cents,stripe_amount_inr,stripe_currency,exchange_rate_used,amount_cents,currency,status,stripe_checkout_session_id,stripe_payment_intent_id,created_at,completed_at,cancellation_reason",
            "limit": "1",
        },
    )
    return payload[0] if payload else None


async def complete_topup(
    *,
    stripe_event_id: str,
    stripe_checkout_session_id: str,
    stripe_payment_intent_id: str | None,
    user_id: str,
    amount_cents: int,
    currency: str,
) -> dict:
    return await execute_rest_rpc(
        path="/rest/v1/rpc/complete_topup",
        payload={
            "target_stripe_event_id": stripe_event_id,
            "target_checkout_session_id": stripe_checkout_session_id,
            "target_payment_intent_id": stripe_payment_intent_id,
            "target_user_id": user_id,
            "target_amount_cents": amount_cents,
            "target_currency": currency,
        },
    )


async def fetch_topups(user_id: str, limit: int = 20) -> list[dict]:
    return await rest_select(
        path="/rest/v1/topups",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,package_id,package_value_usd_cents,stripe_amount_inr,stripe_currency,exchange_rate_used,amount_cents,currency,status,created_at,completed_at,stripe_checkout_session_id,cancellation_reason",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    )
