"""Live authenticated runtime checks; no tokens, keys, or page bodies are printed."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.core.config import settings


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main(probe=False, keys=False):
    local = dotenv_values(ROOT / "apps/web/.env.local")
    print(
        json.dumps(
            {
                "frontend_api_base": local.get("NEXT_PUBLIC_API_BASE_URL"),
                "root_env_exists": (ROOT / ".env").is_file(),
                "supabase_url_present": bool(settings.supabase_url),
                "supabase_credentials_present": bool(
                    settings.supabase_anon_key and settings.supabase_service_role_key
                ),
            }
        )
    )
    private = json.loads(
        (ROOT / "tools/.opencode-test.env.local").read_text(encoding="utf-8")
    )
    with httpx.Client(timeout=60) as client:
        login = client.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_anon_key},
            json={"email": private["email"], "password": private["password"]},
        )
        check(login.status_code == 200, "Test account sign-in failed")
        session = login.json()
        auth = {"Authorization": "Bearer " + session["access_token"]}
        ports = [8000, 8001] if probe else [8000]
        overview = None
        for port in ports:
            for path in ("/dashboard/usage", "/api-keys", "/dashboard/overview"):
                try:
                    response = client.get(
                        f"http://127.0.0.1:{port}/v1{path}", headers=auth
                    )
                    print(
                        json.dumps(
                            {
                                "port": port,
                                "path": path,
                                "status": response.status_code,
                                "missing_supabase": "SUPABASE_URL is not configured"
                                in response.text,
                            }
                        )
                    )
                    if not probe:
                        check(
                            response.status_code == 200,
                            "Authenticated API failed: " + path,
                        )
                    if (
                        port == 8000
                        and path == "/dashboard/overview"
                        and response.status_code == 200
                    ):
                        overview = response.json()
                except httpx.TransportError:
                    print(
                        json.dumps(
                            {"port": port, "path": path, "connection_failed": True}
                        )
                    )
                    check(probe, "Backend unreachable")
        if keys:
            for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
                preflight = client.options(
                    "http://127.0.0.1:8000/v1/api-keys",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "authorization,content-type",
                    },
                )
                check(
                    preflight.status_code == 200
                    and preflight.headers.get("access-control-allow-origin") == origin,
                    "Browser preflight rejected",
                )
            created = client.post(
                "http://127.0.0.1:8000/v1/api-keys",
                headers={**auth, "Origin": "http://127.0.0.1:3000"},
                json={"name": "Runtime repair verification (temporary)"},
            )
            check(created.status_code == 201, "Authenticated key creation failed")
            record = created.json()
            try:
                check(bool(record.get("plaintext_key")), "Key was not returned")
                check(
                    created.headers.get("access-control-allow-origin")
                    == "http://127.0.0.1:3000",
                    "POST CORS header missing",
                )
                listed = client.get("http://127.0.0.1:8000/v1/api-keys", headers=auth)
                check(
                    any(k["id"] == record["id"] for k in listed.json()["data"]),
                    "Created key missing from list",
                )
                print(
                    json.dumps(
                        {
                            "key_create_status": 201,
                            "listed": True,
                            "plaintext_redacted": True,
                        }
                    )
                )
            finally:
                revoked = client.post(
                    f"http://127.0.0.1:8000/v1/api-keys/{record['id']}/revoke",
                    headers=auth,
                )
                check(
                    revoked.status_code == 200,
                    "Temporary verification key cleanup failed",
                )
                print(json.dumps({"temporary_key_revoked": True}))
        if overview and not probe:
            payload = {
                "url": settings.supabase_url,
                "anon_key": settings.supabase_anon_key,
                "session": session,
                "expected_cents": overview["wallet"]["balance_cents"],
                "expected_available_cents": overview["wallet"][
                    "available_balance_cents"
                ],
                "expected_reserved_cents": overview["wallet"]["reserved_cents"],
                "email": private["email"],
            }
            result = subprocess.run(
                ["node", str(ROOT / "tools/verify_dashboard_render.cjs")],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=150,
            )
            # The child only emits a fixed allowlisted summary.
            check(result.returncode == 0, "Authenticated rendered dashboard failed")
            print(json.dumps(json.loads(result.stdout)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--keys", action="store_true")
    args = parser.parse_args()
    try:
        main(args.probe, args.keys)
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else type(exc).__name__)
        sys.exit(1)
