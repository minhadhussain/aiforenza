from __future__ import annotations

import hashlib
import secrets

from app.core.config import settings
from app.repositories.api_keys import fetch_api_key_by_hash
from app.repositories.api_keys import fetch_api_key_for_user
from app.repositories.api_keys import fetch_api_keys_for_user
from app.repositories.api_keys import insert_api_key
from app.repositories.api_keys import revoke_api_key_record
from app.repositories.api_keys import touch_api_key
from app.repositories.supabase_rest import SupabaseRepositoryError


API_KEY_PREFIX = "sk_live_"


class ApiKeyServiceError(Exception):
    pass


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(24)}"


def key_prefix_for(api_key: str) -> str:
    return api_key[:16]


def hash_api_key(api_key: str) -> str:
    payload = f"{settings.api_key_pepper}:{api_key}" if settings.api_key_pepper else api_key
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def mask_key_prefix(prefix: str) -> str:
    visible = prefix[:8]
    return f"{visible}••••••••"


async def create_api_key_record(user_id: str, name: str) -> dict:
    api_key = generate_api_key()
    prefix = key_prefix_for(api_key)
    payload = {
        "user_id": user_id,
        "name": name,
        "key_prefix": prefix,
        "key_hash": hash_api_key(api_key),
    }

    try:
        record = await insert_api_key(payload)
    except SupabaseRepositoryError as exc:
        raise ApiKeyServiceError(str(exc)) from exc

    return {
        "record": record,
        "plaintext_key": api_key,
    }


async def list_api_keys(user_id: str) -> list[dict]:
    try:
        payload = await fetch_api_keys_for_user(user_id)
    except SupabaseRepositoryError as exc:
        raise ApiKeyServiceError(str(exc)) from exc

    return [
        {
            **item,
            "masked_key": mask_key_prefix(item["key_prefix"]),
            "status": "revoked" if item.get("revoked_at") else "active",
        }
        for item in payload
    ]


async def revoke_api_key(user_id: str, key_id: str) -> dict | None:
    try:
        existing = await fetch_api_key_for_user(user_id, key_id)
    except SupabaseRepositoryError as exc:
        raise ApiKeyServiceError(str(exc)) from exc

    if not existing:
        return None

    if existing.get("revoked_at"):
        return {
            **existing,
            "masked_key": mask_key_prefix(existing["key_prefix"]),
            "status": "revoked",
        }

    try:
        record = await revoke_api_key_record(user_id, key_id)
    except SupabaseRepositoryError as exc:
        raise ApiKeyServiceError(str(exc)) from exc

    return {
        **record,
        "masked_key": mask_key_prefix(record["key_prefix"]),
        "status": "revoked",
    }


async def authenticate_api_key(api_key: str) -> dict | None:
    key_hash = hash_api_key(api_key)

    try:
        record = await fetch_api_key_by_hash(key_hash)
    except SupabaseRepositoryError as exc:
        raise ApiKeyServiceError(str(exc)) from exc

    if not record:
        return None

    if record.get("revoked_at"):
        return None

    return record


async def touch_api_key_last_used(key_id: str) -> None:
    try:
        await touch_api_key(key_id)
    except SupabaseRepositoryError as exc:
        raise ApiKeyServiceError(str(exc)) from exc
