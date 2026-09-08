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
    total_tokens: int,
    reference_charge_cents: int,
    customer_charge_cents: int,
    customer_savings_cents: int,
    provider_cost_cents: int | None,
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
            "target_total_tokens": total_tokens,
            "target_reference_charge_cents": reference_charge_cents,
            "target_customer_charge_cents": customer_charge_cents,
            "target_customer_savings_cents": customer_savings_cents,
            "target_provider_cost_cents": provider_cost_cents,
            "target_provider_cost_reference": provider_cost_reference,
            "target_status": status,
        },
    )
