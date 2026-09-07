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
