from datetime import datetime
from datetime import timezone

from app.repositories.supabase_rest import execute_rest_mutation
from app.repositories.supabase_rest import rest_select


async def insert_api_key(payload: dict) -> dict:
    response = await execute_rest_mutation(
        path="/rest/v1/api_keys",
        method="POST",
        json=payload,
        prefer="return=representation",
    )
    return response[0] if isinstance(response, list) else response


async def fetch_api_keys_for_user(user_id: str) -> list[dict]:
    return await rest_select(
        path="/rest/v1/api_keys",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,name,key_prefix,last_used_at,created_at,revoked_at",
            "order": "created_at.desc",
        },
    )


async def fetch_api_key_for_user(user_id: str, key_id: str) -> dict | None:
    payload = await rest_select(
        path="/rest/v1/api_keys",
        params={
            "id": f"eq.{key_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,name,key_prefix,last_used_at,created_at,revoked_at",
            "limit": "1",
        },
    )
    return payload[0] if payload else None


async def revoke_api_key_record(user_id: str, key_id: str) -> dict:
    payload = await execute_rest_mutation(
        path=f"/rest/v1/api_keys?id=eq.{key_id}&user_id=eq.{user_id}",
        method="PATCH",
        json={"revoked_at": datetime.now(timezone.utc).isoformat()},
        prefer="return=representation",
    )
    return payload[0] if isinstance(payload, list) else payload


async def fetch_api_key_by_hash(key_hash: str) -> dict | None:
    payload = await rest_select(
        path="/rest/v1/api_keys",
        params={
            "key_hash": f"eq.{key_hash}",
            "select": "id,user_id,name,key_prefix,last_used_at,created_at,revoked_at",
            "limit": "1",
        },
    )
    return payload[0] if payload else None


async def touch_api_key(key_id: str) -> None:
    await execute_rest_mutation(
        path=f"/rest/v1/api_keys?id=eq.{key_id}",
        method="PATCH",
        json={"last_used_at": datetime.now(timezone.utc).isoformat()},
        prefer="return=minimal",
    )
