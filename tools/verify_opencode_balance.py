"""Use the actual local OpenCode key. Never prints keys or prompt content."""

import asyncio
import json
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "apps/api"))
from diagnose_balance import opencode_keys
from app.services.api_keys import hash_api_key
from app.repositories.supabase_rest import rest_select
from app.repositories.wallets import fetch_wallet
from app.models.openai import ChatCompletionRequest
from app.services.models import get_model_by_slug
from app.services.usage_records import preflight_spending_details
from app.main import app
from fastapi.testclient import TestClient


def saved_request():
    log = Path.home() / ".local/share/opencode/log/2026-09-09T212037.log"
    if not log.exists():
        return None
    text = log.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("requestBodyValues"), dict):
            body = obj["requestBodyValues"]
            if body.get("model") == "gpt-5.4" and "tools" in body:
                return body
    return None


def main():
    keys = opencode_keys()
    if len(keys) != 1:
        raise RuntimeError("Expected one configured AI Forenza key")
    key = keys[0]
    rows = asyncio.run(
        rest_select(
            "/rest/v1/api_keys",
            {"key_hash": "eq." + hash_api_key(key), "select": "id,user_id,revoked_at"},
        )
    )
    if len(rows) != 1 or rows[0]["revoked_at"]:
        raise RuntimeError("Key unavailable")
    user = rows[0]["user_id"]
    before = asyncio.run(fetch_wallet(user))
    print("identity", json.dumps(rows[0]))
    fields = ("balance_cents", "reserved_cents", "available_balance_cents", "currency")
    print("before", json.dumps({k: before[k] for k in fields}))
    with TestClient(app, raise_server_exceptions=False) as client:
        for label, body in (
            (
                "small_direct",
                {
                    "model": "gpt-5.4",
                    "messages": [{"role": "user", "content": "Reply OK"}],
                    "max_completion_tokens": 16,
                    "stream": False,
                },
            ),
            ("saved_opencode", saved_request()),
        ):
            if body is None:
                print(label, "request unavailable")
                continue
            model = asyncio.run(get_model_by_slug(body["model"]))
            print(
                label,
                "preflight",
                json.dumps(
                    preflight_spending_details(ChatCompletionRequest(**body), model)
                ),
            )
            result = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json=body,
            )
            try:
                code = result.json().get("error", {}).get("code")
            except ValueError:
                code = None
            print(label, "http", result.status_code, "error_code", code)
            if result.status_code == 200:
                print(
                    "completion_verified",
                    "[DONE]" in result.text
                    if body.get("stream")
                    else bool(result.json().get("choices")),
                )
    after = asyncio.run(fetch_wallet(user))
    print("after", json.dumps({k: after[k] for k in fields}))
    assert after["reserved_cents"] == before["reserved_cents"], (
        "Unexpected leaked reservation"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Verification incomplete:", type(exc).__name__)
        sys.exit(1)
