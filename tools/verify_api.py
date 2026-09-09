"""Run a bounded, real generated-key check. Does not print credentials/content.

Run from root: python tools/verify_api.py
Uses TestClient with real repositories/provider, not a stale background server.
"""
import asyncio
import os
import secrets
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "apps/api"))

import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.repositories.supabase_rest import build_service_headers


def main():
    base = settings.supabase_url.rstrip("/")
    user_id = token = key_id = None
    with httpx.Client(timeout=30) as remote, TestClient(app) as client:
        try:
            email = f"verify-{uuid4().hex}@example.invalid"
            password = secrets.token_urlsafe(32)
            response = remote.post(base + "/auth/v1/admin/users", headers=build_service_headers(), json={"email":email,"password":password,"email_confirm":True})
            assert response.status_code == 200, "Test user creation failed"
            user_id = response.json()["id"]
            response = remote.post(base + "/auth/v1/token?grant_type=password", headers={"apikey":settings.supabase_anon_key}, json={"email":email,"password":password})
            assert response.status_code == 200, "Test login failed"
            token = response.json()["access_token"]
            auth = {"Authorization": "Bearer " + token}
            overview = client.get("/v1/dashboard/overview",headers=auth)
            assert overview.status_code == 200, "Wallet bootstrap failed"
            before = overview.json()["wallet"]["balance_cents"]
            assert before == 500
            again = client.get("/v1/dashboard/overview",headers=auth)
            assert again.json()["wallet"]["balance_cents"] == 500
            created = client.post("/v1/api-keys",headers=auth,json={"name":"Automated verification"})
            assert created.status_code == 201, "Key creation failed"
            key_id = created.json()["id"]
            key_auth = {"Authorization":"Bearer " + created.json()["plaintext_key"]}
            listed = client.get("/v1/models",headers=key_auth)
            assert listed.status_code == 200, "Generated key authentication failed"
            # Use the actual public Sol identity; no verification aliases.
            model = os.getenv("VERIFY_MODEL", "gpt-5.6-sol")
            for stream in (False, True):
                result = client.post("/v1/chat/completions",headers=key_auth,json={"model":model,"messages":[{"role":"user","content":"Reply OK"}],"max_completion_tokens":16,"stream":stream})
                if result.status_code != 200:
                    error = result.json().get("error",{})
                    print("request rejected:", result.status_code, error.get("code","unknown"))
                    raise RuntimeError("Live completion did not succeed")
                if stream:
                    assert "data: [DONE]" in result.text, "Stream did not settle successfully"
                else:
                    assert result.json()["choices"], "Missing response choices"
                    assert "routing" not in result.json()
                print("completion verified", "streaming" if stream else "non-streaming")
            after = client.get("/v1/dashboard/overview",headers=auth).json()["wallet"]["balance_cents"]
            rows = client.get("/v1/dashboard/usage",headers=auth).json()["data"]
            assert len(rows) == 2
            assert before-after == sum(row["customer_charge_cents"] for row in rows)
            assert before-after > 0, "Configured rate rounded to zero; non-zero debit not proven"
            print("wallet cents:", before, "->", after, "; two persisted usage records")
            assert client.post(f"/v1/api-keys/{key_id}/revoke",headers=auth).status_code == 200
            assert client.get("/v1/models",headers=key_auth).status_code == 401
            assert client.post("/v1/chat/completions",headers=key_auth,json={"model":model,"messages":[{"role":"user","content":"Hello"}]}).status_code == 401
            print("revoked key rejected by models and completions")
        finally:
            if key_id and token:
                client.post(f"/v1/api-keys/{key_id}/revoke",headers={"Authorization":"Bearer " + token})
            # Preserve financial audit rows; disable only this test identity.
            if user_id:
                response = remote.put(base + "/auth/v1/admin/users/" + user_id,headers=build_service_headers(),json={"ban_duration":"876000h"})
                print("test identity disabled:", response.status_code == 200)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Verification incomplete:", type(exc).__name__)
        sys.exit(1)
