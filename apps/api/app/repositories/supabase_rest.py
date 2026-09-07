import httpx

from app.core.config import settings


class SupabaseRepositoryError(Exception):
    pass


def build_rest_url(path: str) -> str:
    if not settings.supabase_url:
        raise SupabaseRepositoryError("SUPABASE_URL is not configured.")
    if not settings.supabase_service_role_key:
        raise SupabaseRepositoryError("SUPABASE_SERVICE_ROLE_KEY is not configured.")
    return f"{settings.supabase_url.rstrip('/')}{path}"


def build_service_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


async def rest_select(path: str, params: dict[str, str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            build_rest_url(path),
            headers={**build_service_headers(), "Accept": "application/json"},
            params=params,
        )

    if response.status_code != 200:
        raise SupabaseRepositoryError(_error_message(response, f"Failed to fetch data from {path}."))

    return response.json()


async def execute_rest_mutation(path: str, method: str, json: dict, prefer: str) -> dict | list[dict] | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(
            method,
            build_rest_url(path),
            headers={**build_service_headers(), "Prefer": prefer, "Accept": "application/json"},
            json=json,
        )

    if response.status_code not in {200, 201, 204}:
        raise SupabaseRepositoryError(_error_message(response, f"Failed to mutate data at {path}."))

    if response.status_code == 204 or not response.content:
        return None

    return response.json()


async def execute_rest_rpc(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            build_rest_url(path),
            headers=build_service_headers(),
            json=payload,
        )

    if response.status_code != 200:
        raise SupabaseRepositoryError(_error_message(response, f"Failed to execute RPC at {path}."))

    data = response.json()
    return data[0] if isinstance(data, list) and data else data


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback

    if isinstance(payload, dict):
        return payload.get("message") or payload.get("details") or payload.get("hint") or fallback

    return fallback
