import httpx

from app.core.config import settings


class SupabaseAuthError(Exception):
    pass


async def fetch_user_for_token(access_token: str) -> dict:
    if not settings.supabase_url:
        raise SupabaseAuthError("SUPABASE_URL is not configured.")

    api_key = settings.supabase_anon_key or settings.supabase_service_role_key
    if not api_key:
        raise SupabaseAuthError("No Supabase API key is configured for token validation.")

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "apikey": api_key,
            },
        )

    if response.status_code != 200:
        raise SupabaseAuthError("Supabase rejected the access token.")

    return response.json()
