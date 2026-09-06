from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.auth import get_current_dashboard_user
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.wallets import bootstrap_user_account
from app.repositories.wallets import build_wallet_summary
from app.repositories.wallets import fetch_transactions
from app.repositories.wallets import fetch_wallet


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
async def get_dashboard_overview(user: dict = Depends(get_current_dashboard_user)) -> dict:
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
    except SupabaseRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    summary = build_wallet_summary(wallet, transactions)

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
