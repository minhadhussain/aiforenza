from app.services.api_keys import hash_api_key
from app.services.api_keys import key_prefix_for
from app.services.api_keys import mask_key_prefix
from app.services.api_keys import authenticate_api_key
from app.services.api_keys import ApiKeyServiceError


def test_hash_api_key_is_stable() -> None:
    assert hash_api_key("demo_key_example") == hash_api_key("demo_key_example")


def test_key_prefix_for_uses_leading_characters() -> None:
    assert key_prefix_for("demo-key-1234567890") == "demo-key-1234567"


def test_mask_key_prefix_obscures_suffix() -> None:
    assert mask_key_prefix("demo-key-123456") == "demo-key••••••••"


def test_authenticate_api_key_returns_none_for_revoked_key(monkeypatch) -> None:
    async def fake_fetch_api_key_by_hash(key_hash: str):
        assert key_hash == hash_api_key("demo_key_example")
        return {
            "id": "key-1",
            "user_id": "user-1",
            "name": "Revoked",
            "key_prefix": "demo-key-123456",
            "revoked_at": "2026-09-07T00:00:00Z",
        }

    monkeypatch.setattr("app.services.api_keys.fetch_api_key_by_hash", fake_fetch_api_key_by_hash)

    import asyncio

    result = asyncio.run(authenticate_api_key("demo_key_example"))
    assert result is None
