"""Read-only balance diagnostics. Never prints credentials or prompt content."""

import asyncio
import json
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "apps/api"))
from app.services.api_keys import hash_api_key
from app.repositories.supabase_rest import rest_select
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.services.usage_records import estimate_preflight_charge_cents


def opencode_keys():
    path = Path.home() / ".local/share/opencode/auth.json"
    if not path.exists():
        print("OpenCode credential store not found")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = []
    for provider, value in data.items():
        if "forenza" not in provider.lower():
            continue
        if isinstance(value, dict) and isinstance(value.get("key"), str):
            keys.append(value["key"])
    for config in (
        Path.home() / ".opencode/opencode.json",
        Path.home() / "OneDrive/Desktop/opencode.json",
        Path.home() / "bug-bounty/opencode.jsonc",
    ):
        if not config.exists():
            continue
        text = config.read_text(encoding="utf-8")
        if not any(
            marker in text.lower()
            for marker in ("forenza", "localhost:8000", "127.0.0.1:8000")
        ):
            continue
        print("Relevant OpenCode config:", str(config))
        for field in (
            "model",
            "small_model",
            "baseURL",
            "maxTokens",
            "maxOutputTokens",
            "output",
        ):
            for match in re.finditer(
                r'"' + field + r'"\s*:\s*("[^"\n]*"|[0-9]+)', text
            ):
                value = match.group(1)
                if "sk_" not in value and "key" not in value.lower():
                    print("config", field, value)
        keys.extend(re.findall(r"(?<![\w])sk_(?:af_)?live_[A-Za-z0-9_-]+", text))
    keys = list(dict.fromkeys(keys))
    print("AI Forenza credentials found:", len(keys))
    return keys


async def main():
    for key in opencode_keys():
        rows = await rest_select(
            "/rest/v1/api_keys",
            {
                "key_hash": "eq." + hash_api_key(key),
                "select": "id,user_id,revoked_at,last_used_at",
            },
        )
        if not rows:
            print("Configured key does not match this backend hash configuration")
            continue
        record = rows[0]
        print("matched_key", json.dumps(record))
        user_id = record["user_id"]
        wallets = await rest_select(
            "/rest/v1/wallets",
            {"user_id": "eq." + user_id, "select": "id,user_id,balance_cents,currency"},
        )
        holds = await rest_select(
            "/rest/v1/wallet_reservations",
            {
                "user_id": "eq." + user_id,
                "select": "request_id,api_key_id,model_id,amount_cents,created_at",
                "order": "created_at.asc",
            },
        )
        print("wallet", json.dumps(wallets))
        print("holds", json.dumps(holds))
        total_held = sum(item["amount_cents"] for item in holds)
        print(
            "reserved_cents",
            total_held,
            "available_cents",
            wallets[0]["balance_cents"] - total_held,
        )
        # Only extract request status/error categories, never raw log lines or bodies.
        log_dir = Path.home() / ".local/share/opencode/log"
        for log in sorted(log_dir.glob("*.log"))[-2:]:
            text = log.read_text(encoding="utf-8", errors="replace")
            if "2026-09-09" in log.name:
                print(
                    "request_ids_in_log",
                    sorted(set(re.findall(r"req_[a-f0-9]{32}", text))),
                )
                print(
                    "output_limits_in_log",
                    sorted(
                        set(
                            re.findall(
                                r'(?:max_tokens|max_completion_tokens)\\?"\s*:\s*(\d+)',
                                text,
                            )
                        )
                    ),
                )
                decoder = json.JSONDecoder()
                seen = set()
                for match in re.finditer(r"\{", text):
                    try:
                        obj, _ = decoder.raw_decode(text[match.start() :])
                    except ValueError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    body = obj.get("requestBodyValues")
                    if isinstance(body, dict):
                        summary = {
                            "fields": list(body),
                            "model": body.get("model"),
                            "max_tokens": body.get("max_tokens"),
                            "max_completion_tokens": body.get("max_completion_tokens"),
                            "messages": len(body.get("messages", [])),
                            "tools": len(body.get("tools", [])),
                            "status": obj.get("statusCode"),
                        }
                        encoded = json.dumps(summary)
                        if encoded not in seen:
                            print("request_shape", encoded)
                            seen.add(encoded)
            for pattern in (
                r'"statusCode"\s*:\s*(\d+)',
                r'"code"\s*:\s*"(insufficient_balance|provider_unavailable|unsupported_parameter|invalid_request_error)"',
                r"(max_tokens|max_completion_tokens)[^\n]{0,0}",
            ):
                matches = re.findall(pattern, text)
                if matches:
                    print("log_category", log.name, pattern, sorted(set(matches)))
        for log in (ROOT / "apps/api").glob("*.log"):
            text = log.read_text(encoding="utf-8", errors="replace")
            codes = re.findall(
                r"(?:HTTPStatusError|ProviderGatewayError|OpenAIAPIError|ReadTimeout|ConnectError|ValidationError)",
                text,
            )
            if codes:
                print("backend_log_errors", log.name, sorted(set(codes)))
        models = await rest_select(
            "/rest/v1/models", {"enabled": "eq.true", "select": "*"}
        )
        for row in models:
            model = CatalogModel.model_validate(row)
            for output in (32, 1024, 8192, 32768):
                req = ChatCompletionRequest(
                    model=model.slug,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_completion_tokens=output,
                )
                print(
                    "preflight",
                    model.slug,
                    "output_limit",
                    output,
                    "customer_cents",
                    estimate_preflight_charge_cents(req, model),
                )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print("Diagnostics failed:", type(exc).__name__)
        sys.exit(1)
