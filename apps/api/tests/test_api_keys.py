from app.services.api_keys import hash_api_key
from app.services.api_keys import key_prefix_for
from app.services.api_keys import mask_key_prefix


def test_hash_api_key_is_stable() -> None:
    assert hash_api_key("demo_key_example") == hash_api_key("demo_key_example")


def test_key_prefix_for_uses_leading_characters() -> None:
    assert key_prefix_for("demo-key-1234567890") == "demo-key-1234567"


def test_mask_key_prefix_obscures_suffix() -> None:
    assert mask_key_prefix("demo-key-123456") == "demo-key••••••••"
