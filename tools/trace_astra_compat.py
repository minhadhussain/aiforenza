"""Capture the installed OpenCode SDK's real wire shape without inference or secrets.

The capture target is loopback-only, never logs headers/prompts, and returns a
deliberate 400. --probe also makes bounded direct Azure compatibility probes.
"""

import argparse
import json
import os
import subprocess
import threading
import re
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from configure_opencode_global import executable, global_path, ROOT
from app.core.config import settings

EFFORTS = ("low", "medium", "high", "xhigh", "max")


def client_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENCODE_", "AZURE_", "SUPABASE_", "STRIPE_", "DATABASE_", "API_KEY_", "LITELLM_"))}
    env.update(OPENCODE_DISABLE_AUTOUPDATE="true", OPENCODE_DISABLE_DEFAULT_PLUGINS="true", OPENCODE_DISABLE_CLAUDE_CODE="true", OPENCODE_DISABLE_PROJECT_CONFIG="true")
    return env


def capture():
    config = json.loads(global_path().read_text(encoding="utf-8"))
    entry = config["provider"]["aiforenza"]["models"]["gpt-6-astra"]
    print(json.dumps({"opencode_version": subprocess.check_output([str(executable()), "--version"], text=True).strip(), "sdk": config["provider"]["aiforenza"]["npm"], "astra_reasoning": entry.get("reasoning"), "astra_default_effort": entry.get("options", {}).get("reasoningEffort"), "variant_names": list(entry.get("variants", {})), "limits": entry.get("limit")}))
    seen = []

    class Recorder(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"model": body.get("model") if body.get("model") == "gpt-6-astra" else "other", "reasoning_effort": body.get("reasoning_effort") if body.get("reasoning_effort") in (*EFFORTS, "none", "minimal") else None, "reasoning_object_present": "reasoning" in body, "reasoningEffort_present": "reasoningEffort" in body, "stream": body.get("stream") is True, "max_tokens": body.get("max_tokens"), "max_completion_tokens": body.get("max_completion_tokens"), "tools_count": len(body.get("tools", [])), "temperature_present": "temperature" in body, "top_p_present": "top_p" in body, "reasoningSummary_present": "reasoningSummary" in body})
            result = b'{"error":{"message":"Local request-shape capture complete","type":"invalid_request_error","code":"capture_complete"}}'
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(result)))
            self.end_headers()
            self.wfile.write(result)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for variant in ("baseline", *EFFORTS):
            override = {"provider": {"aiforenza": {"options": {"baseURL": f"http://127.0.0.1:{server.server_port}/v1"}}}, "share": "disabled", "agent": {"title": {"disable": True}}}
            if variant != "baseline":
                override["provider"]["aiforenza"]["models"] = {"gpt-6-astra": {"reasoning": True, "variants": {v: {"reasoningEffort": v} for v in EFFORTS}}}
            env = client_env()
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps(override)
            args = [str(executable()), "run", "--print-logs", "--pure", "--format", "json", "--model", "aiforenza/gpt-6-astra", "--title", "Request shape capture"]
            if variant != "baseline":
                args += ["--variant", variant]
            before = len(seen)
            result = subprocess.run([*args, "Reply OK without using tools."], cwd=ROOT / "tools/.opencode-test-workspace", env=env, capture_output=True, timeout=90, text=True, encoding="utf-8", errors="replace")
            events = []
            for line in result.stdout.splitlines():
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        events.append(item)
                except ValueError:
                    pass
            if not seen[before:]:
                # Before any HTTP request, retain only a startup-error vocabulary.
                error_text = result.stderr + " ".join(str(e.get("error", {}).get("data", {}).get("message", "")) for e in events)
                print(json.dumps({"startup_terms": [term for term in ("session", "agent", "directory", "not found", "Cannot", "tui", "migrate", "Bun", "fetch", "ENOENT", "EPERM", "readonly", "permission", "failed", "build", "default", "resolve", "state", "database", "undefined", "null") if term.lower() in error_text.lower()], "error_data_keys": [list(e.get("error", {}).get("data", {})) for e in events]}))
                print(json.dumps({"exception_categories": sorted(set(re.findall(r"\b[A-Z][A-Za-z]+(?:Error|Exception)\b", error_text))), "services": sorted(set(re.findall(r"service=([a-zA-Z_.-]+)", error_text))), "startup_error_terms": [term for term in ("column", "table", "socket", "certificate", "unsupported", "unauthorized", "SQLite", "constraint", "INSERT", "project", "branch", "git", "pure", "bootstrap", "spawn", "provider", "request", "connection", "runtime", "type", "invalid") if term.lower() in error_text.lower()]}))
            print(json.dumps({"selected_variant": variant, "captured_requests": seen[before:], "exit_code": result.returncode, "output_bytes": len(result.stdout), "error_names": [e.get("error", {}).get("name") for e in events if e.get("type") == "error"], "categories": [term for term in ("Session not found", "SQLITE_BUSY", "Model not found", "Unknown argument", "Configuration is invalid", "Unable to connect", "capture_complete", "Invalid config", "No provider", "Failed to resolve") if term in result.stdout + result.stderr]}), flush=True)
    finally:
        server.shutdown()
        server.server_close()


def probe():
    # Fixed synthetic prompt; response content/error messages are never printed.
    with httpx.Client(timeout=120) as client:
        inventory = client.get(settings.azure_endpoint.rstrip("/") + "/models", headers={"api-key": settings.azure_api_key})
        rows = [row for row in inventory.json().get("data", []) if row.get("id") == "gpt-6-astra"]
        print(json.dumps({"inventory_status": inventory.status_code, "astra_matches": len(rows), "api_host": urlsplit(settings.azure_endpoint).hostname, "api_path": "/openai/v1", "dated_api_version": False, "inventory_fields": list(rows[0]) if rows else []}))
        for effort, tools in (("none", False), ("medium", False), ("medium", True), ("max", False)):
            body = {"model": "gpt-6-astra", "messages": [{"role": "user", "content": "Reply OK."}], "max_completion_tokens": 128, "reasoning_effort": effort}
            if tools:
                body["tools"] = [{"type": "function", "function": {"name": "read_fixture", "parameters": {"type": "object", "properties": {}}}}]
            response = client.post(settings.azure_endpoint.rstrip("/") + "/chat/completions", headers={"api-key": settings.azure_api_key}, json=body)
            payload = response.json()
            error = payload.get("error") or {}
            message = str(error.get("message", ""))
            print(json.dumps({"effort": effort, "tools": tools, "provider_status": response.status_code, "response_model": payload.get("model") if re.fullmatch(r"[A-Za-z0-9._-]{1,120}", str(payload.get("model", ""))) else None, "error_code": error.get("code") if error.get("code") in ("unsupported_parameter", "unsupported_value", "invalid_request_error") else None, "mentions": [value for value in ("reasoning_effort", "none", "low", "medium", "high", "xhigh", "max", "tools", "Responses", "/v1/responses") if value in message], "usage": {k: v for k, v in (payload.get("usage") or {}).items() if k in ("prompt_tokens", "completion_tokens", "total_tokens") and isinstance(v, int)}}), flush=True)
        for effort in ("medium", "max"):
            response = client.post(settings.azure_endpoint.rstrip("/") + "/responses", headers={"api-key": settings.azure_api_key}, json={"model": "gpt-6-astra", "input": "Reply OK.", "max_output_tokens": 128, "reasoning": {"effort": effort}, "store": False, "tools": [{"type": "function", "name": "read_fixture", "parameters": {"type": "object", "properties": {}}}]})
            result = response.json()
            error = result.get("error") or {}
            message = str(error.get("message", ""))
            print(json.dumps({"api": "responses", "effort": effort, "tools": True, "provider_status": response.status_code, "echoed_effort": (result.get("reasoning") or {}).get("effort"), "mentions": [value for value in ("effort", "none", "low", "medium", "high", "xhigh", "max", "tools") if value in message]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    try:
        probe() if args.probe else capture()
    except Exception as exc:
        print("Compatibility trace stopped:", type(exc).__name__)
        raise SystemExit(1)
