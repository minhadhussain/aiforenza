"""Run one local Next + FastAPI stack and Docker Redis. Ctrl+C stops owned app trees."""

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.core.config import settings
from dotenv import dotenv_values


def check_configuration():
    required = (
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
    )
    missing = [
        field.upper() for field in required if not getattr(settings, field).strip()
    ]
    if missing:
        raise RuntimeError(
            "Missing backend settings: "
            + ", ".join(missing)
            + ". Configure the root .env."
        )
    web = dotenv_values(ROOT / "apps/web/.env.local")
    base = os.environ.get("NEXT_PUBLIC_API_BASE_URL") or web.get(
        "NEXT_PUBLIC_API_BASE_URL"
    )
    if base not in ("http://localhost:8000/v1", "http://127.0.0.1:8000/v1"):
        raise RuntimeError(
            "Local frontend NEXT_PUBLIC_API_BASE_URL must point to port 8000 /v1."
        )


def assert_ports_free():
    for port in (3000, 3001, 8000, 8001):
        for host in ("127.0.0.1", "::1"):
            family = socket.AF_INET6 if host == "::1" else socket.AF_INET
            with socket.socket(family) as sock:
                sock.settimeout(0.3)
                if sock.connect_ex((host, port)) == 0:
                    raise RuntimeError(
                        f"Port {port} is occupied; stop the old dev stack first. No duplicate servers started."
                    )


def stop(child):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True
        )
    else:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()


def main():
    check_configuration()
    assert_ports_free()
    subprocess.run(["docker", "compose", "up", "-d", "redis"], cwd=ROOT, check=True)
    ping = subprocess.run(
        ["docker", "compose", "exec", "-T", "redis", "redis-cli", "ping"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if ping.stdout.strip() != "PONG":
        raise RuntimeError("Redis did not pass readiness check")
    children = []
    try:
        options = {"cwd": ROOT, "start_new_session": os.name != "nt"}
        # Explicit app directory and env file; no cwd-dependent configuration or port fallback.
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    str(ROOT / "apps/api"),
                    "--env-file",
                    str(ROOT / ".env"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--reload",
                    "--reload-dir",
                    str(ROOT / "apps/api/app"),
                ],
                **options,
            )
        )
        env = os.environ.copy()
        # Do not pass backend credentials to the frontend. Next loads its own .env.local.
        for key in list(env):
            if key.startswith(
                (
                    "AZURE_",
                    "STRIPE_",
                    "DATABASE_",
                    "API_KEY_",
                    "LITELLM_",
                    "SUPABASE_SERVICE_",
                )
            ):
                env.pop(key)
        children.append(
            subprocess.Popen(
                [
                    "node",
                    str(ROOT / "node_modules/next/dist/bin/next"),
                    "dev",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    "3000",
                ],
                cwd=ROOT / "apps/web",
                env=env,
                start_new_session=os.name != "nt",
            )
        )
        print(
            "Dev stack: frontend http://127.0.0.1:3000 | backend http://127.0.0.1:8000 | Redis Docker",
            flush=True,
        )
        while all(child.poll() is None for child in children):
            time.sleep(1)
        raise RuntimeError(
            "A dev process exited; stopping its companion to prevent a partial stack."
        )
    finally:
        for child in reversed(children):
            stop(child)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Dev servers stopped. Docker Redis remains available.")
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Dev startup failed: " + type(exc).__name__
        )
        sys.exit(1)
