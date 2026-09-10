"""Account-scoped operational activity, separate from authoritative billing."""

import logging

from app.repositories.supabase_rest import execute_rest_rpc

logger = logging.getLogger("aiforenza.activity")


async def record_rejection(
    *, request_id, user_id, api_key_id, model, code, http_status
):
    try:
        await execute_rest_rpc(
            "/rest/v1/rpc/record_request_rejection",
            {
                "target_request_id": request_id,
                "target_user_id": user_id,
                "target_api_key_id": api_key_id,
                "target_model_slug": model,
                "target_error_code": code,
                "target_http_status": http_status,
            },
        )
    except Exception:
        # Do not turn a rejected request into a retryable failure or log DB secrets.
        logger.warning("Rejection audit unavailable request_id=%s", request_id)


async def fetch_activity(
    user_id,
    *,
    page=1,
    page_size=25,
    model=None,
    api_key_id=None,
    status=None,
    as_of=None,
):
    return await execute_rest_rpc(
        "/rest/v1/rpc/dashboard_activity",
        {
            "target_user_id": user_id,
            "page_number": page,
            "page_size": page_size,
            "filter_model": model,
            "filter_key": str(api_key_id) if api_key_id else None,
            "filter_status": status,
            "snapshot_at": as_of.isoformat() if as_of else None,
        },
    )
