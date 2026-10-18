import httpx
import re

from app.core.config import settings
from app.services.supabase_http import supabase_http_client


class SupabaseRepositoryError(Exception):
    pass


_TABLE_PATH = re.compile(r"/rest/v1/[a-z][a-z0-9_]*")
_RPC_PATH = re.compile(r"/rest/v1/rpc/[a-z][a-z0-9_]*")
_PUBLIC_RPC_ERRORS = {"insufficient_balance", "team_already_claimed", "invalid_team_id", "campaign_inactive"}
_SELECT = re.compile(r"[a-z][a-z0-9_]*(?:,[a-z][a-z0-9_]*)*(?:,model:models\(slug,display_name\))?")
_ORDER = re.compile(r"(?:created_at|released_at|display_name|slug)\.(?:asc|desc)")
_EQUALITY_FILTERS = {
    "id", "user_id", "api_key_id", "model_id", "key_hash", "slug", "enabled",
    "billing_source", "claimed_by_user_id", "status", "request_id", "reference_id",
    "stripe_checkout_session_id",
}


def validate_query_params(params: dict[str, str], *, mutation: bool = False) -> dict[str, str]:
    """Allow only the query grammar used by repositories, with literal values.

    URL encoding alone does not constrain PostgREST's operators/projections.
    Never forward client-supplied query dictionaries to the service-role client.
    This gate supplements PostgreSQL's parameter binding; it does not sanitize SQL.
    """
    if not isinstance(params, dict):
        raise SupabaseRepositoryError("Invalid database query parameters.")
    validated = {}
    for name, value in params.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise SupabaseRepositoryError("Invalid database query parameters.")
        if name == "select" and not mutation:
            valid = value == "*" or _SELECT.fullmatch(value) is not None
        elif name == "order" and not mutation:
            valid = _ORDER.fullmatch(value) is not None
        elif name == "limit" and not mutation:
            valid = re.fullmatch(r"[1-9][0-9]{0,4}", value) is not None and int(value) <= 10_000
        elif name in _EQUALITY_FILTERS:
            # The suffix is data, including quotes, SQL text, '&', and '#'.
            # HTTPX encodes it as one value instead of appending URL fragments.
            valid = value.startswith("eq.")
        elif name == "created_at" and not mutation:
            valid = value.startswith("gte.") and len(value) > 4
        else:
            valid = False
        if not valid:
            raise SupabaseRepositoryError("Unsupported database query structure.")
        validated[name] = value
    return validated


def build_rest_url(path: str, *, rpc: bool = False) -> str:
    # Resource names are application-owned identifiers. Values belong in encoded
    # query parameters or JSON RPC arguments, never in a URL/SQL fragment.
    pattern = _RPC_PATH if rpc else _TABLE_PATH
    if not isinstance(path, str) or not pattern.fullmatch(path):
        raise SupabaseRepositoryError("Invalid database endpoint.")
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
    url = build_rest_url(path)
    params = validate_query_params(params)
    async with supabase_http_client() as client:
        response = await client.get(
            url,
            headers={**build_service_headers(), "Accept": "application/json"},
            params=params,
        )

    if response.status_code != 200:
        raise SupabaseRepositoryError(_error_message(response, f"Failed to fetch data from {path}."))

    return response.json()


async def execute_rest_mutation(path: str, method: str, json: dict, prefer: str, *, params: dict[str, str] | None = None) -> dict | list[dict] | None:
    url = build_rest_url(path)
    if method not in {"POST", "PATCH"}:
        raise SupabaseRepositoryError("Unsupported database mutation.")
    if params is not None and not isinstance(params, dict):
        raise SupabaseRepositoryError("Invalid database query parameters.")
    if method == "PATCH":
        identifier = (params or {}).get("id", "")
        if not isinstance(identifier, str) or not identifier.startswith("eq.") or len(identifier) == 3:
            raise SupabaseRepositoryError("Database updates require an explicit record filter.")
    params = validate_query_params(params if params is not None else {}, mutation=True)
    if prefer not in {"return=minimal", "return=representation"}:
        raise SupabaseRepositoryError("Unsupported database mutation preference.")
    async with supabase_http_client() as client:
        response = await client.request(
            method,
            url,
            headers={**build_service_headers(), "Prefer": prefer, "Accept": "application/json"},
            json=json,
            params=params,
        )

    if response.status_code not in {200, 201, 204}:
        raise SupabaseRepositoryError(_error_message(response, f"Failed to mutate data at {path}."))

    if response.status_code == 204 or not response.content:
        return None

    return response.json()


async def execute_rest_rpc(path: str, payload: dict) -> dict:
    url = build_rest_url(path, rpc=True)
    async with supabase_http_client() as client:
        response = await client.post(
            url,
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

    if isinstance(payload, dict) and payload.get("code") == "P0001":
        message = payload.get("message")
        if isinstance(message, str) and message in _PUBLIC_RPC_ERRORS:
            return message

    # Do not reflect SQL syntax, schema details, query fragments, or returned
    # database values through routes that expose repository error messages.
    return fallback
