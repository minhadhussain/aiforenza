from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from typing import Literal
from uuid import UUID
from app.repositories.activity import fetch_activity

from app.repositories.dashboard import fetch_usage_summary
from app.api.deps.auth import get_current_dashboard_user
from app.repositories.dashboard import fetch_usage_records
from app.repositories.models import fetch_enabled_models
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.wallets import bootstrap_user_account
from app.repositories.wallets import build_wallet_summary
from app.repositories.wallets import fetch_transactions
from app.repositories.wallets import fetch_wallet
from app.services.models import serialize_dashboard_models
from app.services.stripe_payments import list_user_topups


router = APIRouter()


@router.get("/account/me")
async def get_current_account(user: dict = Depends(get_current_dashboard_user)) -> dict:
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "app_metadata": user.get("app_metadata", {}),
        "user_metadata": user.get("user_metadata", {}),
    }


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    user: dict = Depends(get_current_dashboard_user),
) -> dict:
    user_id = user.get("id")
    email = user.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is missing required account data.",
        )

    try:
        bootstrap = await bootstrap_user_account(user_id, email)
        wallet = await fetch_wallet(user_id)
        transactions = await fetch_transactions(user_id)
        usage_summary = await fetch_usage_summary(user_id)
    except SupabaseRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    summary = build_wallet_summary(wallet, transactions)
    summary["metrics"].update(usage_summary)

    return {
        "profile": {
            "id": user_id,
            "email": email,
        },
        "wallet": summary["wallet"],
        "transactions": summary["transactions"],
        "metrics": summary["metrics"],
        "bootstrap": {
            "trial_granted": bool(bootstrap.get("trial_granted", False)),
            "wallet_id": bootstrap.get("wallet_id"),
        },
    }


@router.get("/dashboard/transactions")
async def get_dashboard_transactions(
    user: dict = Depends(get_current_dashboard_user),
) -> dict:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is missing required account data.",
        )

    try:
        transactions = await fetch_transactions(user_id, limit=50)
    except SupabaseRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return {"data": transactions}


@router.get("/dashboard/usage")
async def get_dashboard_usage(user: dict = Depends(get_current_dashboard_user)) -> dict:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is missing required account data.",
        )

    try:
        records = await fetch_usage_records(user_id, limit=50)
    except SupabaseRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return {"data": records}


@router.get("/dashboard/models")
async def get_dashboard_models(_: dict = Depends(get_current_dashboard_user)) -> dict:
    try:
        models = await fetch_enabled_models()
    except SupabaseRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return {"data": serialize_dashboard_models(models)}


@router.get("/dashboard/activity")
async def get_dashboard_activity(
    user: dict = Depends(get_current_dashboard_user),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=25, ge=1, le=100),
    model: str | None = Query(
        default=None, min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._/-]+$"
    ),
    api_key_id: UUID | None = None,
    activity_status: Literal["billed", "unsettled", "rejected", "released"]
    | None = None,
    as_of: datetime | None = None,
) -> dict:
    if as_of and as_of.tzinfo is None:
        raise HTTPException(status_code=422, detail="as_of must include a timezone")
    try:
        payload = await fetch_activity(
            user["id"],
            page=page,
            page_size=page_size,
            model=model,
            api_key_id=api_key_id,
            status=activity_status,
            as_of=as_of,
        )
    except SupabaseRepositoryError as exc:
        raise HTTPException(
            status_code=503, detail="Activity history temporarily unavailable."
        ) from exc
    return {**payload, "account": {"id": user["id"], "email": user.get("email")}}


@router.get("/dashboard/topups")
async def get_dashboard_topups(
    user: dict = Depends(get_current_dashboard_user),
) -> dict:
    return {"data": await list_user_topups(user["id"])}
