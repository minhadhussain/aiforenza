from app.repositories.supabase_rest import execute_rest_rpc


async def reserve_usage(request_id: str, user_id: str, api_key_id: str, model_id: str, amount_cents: int) -> dict:
    return await execute_rest_rpc("/rest/v1/rpc/reserve_usage", {
        "target_request_id": request_id, "target_user_id": user_id,
        "target_api_key_id": api_key_id, "target_model_id": model_id,
        "target_amount_cents": amount_cents,
    })
