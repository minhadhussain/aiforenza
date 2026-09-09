from app.repositories.supabase_rest import rest_select
from app.repositories.supabase_rest import build_service_headers, SupabaseRepositoryError
from app.core.config import settings
import httpx
from datetime import datetime, timezone
from uuid import UUID


async def fetch_profile(user_id: str) -> dict | None:
    payload = await rest_select(
        path="/rest/v1/profiles",
        params={
            "id": f"eq.{user_id}",
            "select": "id,email,created_at,updated_at",
            "limit": "1",
        },
    )
    if not payload:
        return None
    try:
        identifier = str(UUID(user_id))
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{identifier}", headers=build_service_headers())
        if response.status_code == 404:
            return None
        response.raise_for_status()
        user = response.json()
        banned = user.get("banned_until")
        if user.get("deleted_at") or (banned and datetime.fromisoformat(banned.replace("Z", "+00:00")) > datetime.now(timezone.utc)):
            return None
    except (ValueError, httpx.HTTPError) as exc:
        raise SupabaseRepositoryError("Account validation unavailable") from exc
    return payload[0]
