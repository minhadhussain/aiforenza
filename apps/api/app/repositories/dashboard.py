from datetime import datetime
from datetime import timezone

from app.repositories.supabase_rest import rest_select


async def fetch_usage_records(user_id: str, limit: int = 50) -> list[dict]:
    return await rest_select(
        path="/rest/v1/usage_records",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,request_id,input_tokens,output_tokens,cached_input_tokens,customer_charge_cents,status,created_at,model:models(slug,display_name)",
            "order": "created_at.desc",
            "limit": str(limit),
        },
    )


async def fetch_usage_summary(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    today_records = await rest_select(
        path="/rest/v1/usage_records",
        params={
            "user_id": f"eq.{user_id}",
            "created_at": f"gte.{day_start}",
            "select": "customer_charge_cents,request_id",
            "limit": "1000",
        },
    )

    month_records = await rest_select(
        path="/rest/v1/usage_records",
        params={
            "user_id": f"eq.{user_id}",
            "created_at": f"gte.{month_start}",
            "select": "customer_charge_cents,request_id",
            "limit": "5000",
        },
    )

    all_records = await rest_select(
        path="/rest/v1/usage_records",
        params={
            "user_id": f"eq.{user_id}",
            "select": "request_id",
            "limit": "5000",
        },
    )

    return {
        "today_usage_cents": sum(int(item.get("customer_charge_cents", 0) or 0) for item in today_records),
        "month_usage_cents": sum(int(item.get("customer_charge_cents", 0) or 0) for item in month_records),
        "api_request_count": len(all_records),
    }
