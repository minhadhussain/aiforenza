from collections.abc import Mapping

from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.supabase_rest import execute_rest_rpc
from app.repositories.supabase_rest import rest_select


async def bootstrap_user_account(user_id: str, email: str) -> dict:
    return await execute_rest_rpc(
        path="/rest/v1/rpc/bootstrap_user_account",
        payload={"target_user_id": user_id, "target_email": email},
    )


async def fetch_wallet(user_id: str) -> dict | None:
    payload = await rest_select(
        path="/rest/v1/wallets",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,user_id,balance_cents,currency,created_at,updated_at",
            "limit": "1",
        },
    )
    return payload[0] if payload else None


async def fetch_transactions(user_id: str, limit: int = 20) -> list[dict]:
    return await rest_select(
        path="/rest/v1/transactions",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,type,amount_cents,balance_after_cents,description,reference_id,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    )


def build_wallet_summary(wallet: Mapping[str, object] | None, transactions: list[dict]) -> dict:
    if wallet is None:
        return {
            "wallet": None,
            "transactions": transactions,
            "metrics": {
                "current_balance_cents": 0,
                "transaction_count": len(transactions),
                "trial_credit_granted": False,
            },
        }

    return {
        "wallet": dict(wallet),
        "transactions": transactions,
        "metrics": {
            "current_balance_cents": int(wallet.get("balance_cents", 0) or 0),
            "transaction_count": len(transactions),
            "trial_credit_granted": any(tx.get("type") == "FREE_TRIAL" for tx in transactions),
        },
    }
