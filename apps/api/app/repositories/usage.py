from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.supabase_rest import execute_rest_rpc


async def record_usage_charge(
    *,
    user_id: str,
    api_key_id: str,
    model_id: str,
    request_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    customer_charge_cents: int,
    provider_cost_reference: str,
    status: str,
) -> dict:
    return await execute_rest_rpc(
        path="/rest/v1/rpc/record_usage_charge",
        payload={
            "target_user_id": user_id,
            "target_api_key_id": api_key_id,
            "target_model_id": model_id,
            "target_request_id": request_id,
            "target_input_tokens": input_tokens,
            "target_output_tokens": output_tokens,
            "target_cached_input_tokens": cached_input_tokens,
            "target_customer_charge_cents": customer_charge_cents,
            "target_provider_cost_reference": provider_cost_reference,
            "target_status": status,
        },
    )
