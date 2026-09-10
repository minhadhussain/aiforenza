"""Read-only, secret-safe inspection of the specifically reported $1.26 hold."""

import asyncio
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from opencode_live_test import ROOT, ORIGINAL, snapshot, state
from app.repositories.supabase_rest import rest_select

RID = "req_0c4667a644b044c3bc46e11e9f38e656"
START = datetime(2026, 9, 10, 20, 26, 40, tzinfo=timezone.utc).timestamp() * 1000
END = datetime(2026, 9, 10, 20, 28, 40, tzinfo=timezone.utc).timestamp() * 1000
TERMS = (
    "ReadTimeout",
    "ConnectTimeout",
    "ConnectError",
    "CancelledError",
    "missing_usage",
    "provider_unavailable",
    "usage_reconciliation_required",
    "billing_unavailable",
    "pricing_limit_exceeded",
    "unsupported_parameter",
    "stream interrupted",
    "invalid_stream",
    "insufficient_balance",
    "HTTPStatusError",
    "request_too_large",
    "APIError",
    "API request failed",
)


def safe_summary(text):
    return {
        "fingerprint": hashlib.sha256(text.encode()).hexdigest(),
        "request_ids": sorted(set(re.findall(r"req_[a-f0-9]{32}", text))),
        "categories": [term for term in TERMS if term.lower() in text.lower()],
        "http_statuses": sorted(
            set(
                re.findall(
                    r'(?:statusCode["\s:=]+|HTTP/1\.1["\s]+)([245][0-9]{2})', text
                )
            )
        ),
    }


def main():
    private = state()
    wallet = snapshot(private["user_id"])
    print(
        json.dumps(
            {
                "wallet": {
                    k: wallet["wallet"][k]
                    for k in (
                        "balance_cents",
                        "reserved_cents",
                        "available_balance_cents",
                    )
                },
                "hold": [h for h in wallet["holds"] if h["request_id"] == RID],
            }
        )
    )
    home = Path.home() / ".local/share/opencode"
    paths = (
        list((ROOT / "tools").glob("*.log"))
        + list((ROOT / "apps/api").glob("*.log"))
        + list((home / "log").glob("*.log"))
    )
    for path in paths:
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if RID in line or re.search(r"2026-09-10T20:2[67]:", line):
                print(
                    json.dumps(
                        {"source": path.name, "line": number, **safe_summary(line)}
                    )
                )
    db = home / "opencode.db"
    connection = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    try:
        for table in ("message", "part"):
            columns = {r[1] for r in connection.execute(f"pragma table_info({table})")}
            if not {"data", "time_created", "time_updated"}.issubset(columns):
                continue
            fields = [
                f
                for f in (
                    "id",
                    "session_id",
                    "message_id",
                    "time_created",
                    "time_updated",
                    "data",
                )
                if f in columns
            ]
            cursor = connection.execute(
                f"select {','.join(fields)} from {table} where (time_created <= ? and time_updated >= ?) or data like ?",
                (END, START, "%" + RID + "%"),
            )
            for values in cursor:
                row = dict(zip(fields, values))
                raw = row.pop("data")
                obj = json.loads(raw)
                # Do not treat tool output containing earlier diagnostic reports as original evidence.
                kind = obj.get("type") or obj.get("role")
                if kind not in ("assistant", "step-finish"):
                    if RID in raw:
                        print(
                            json.dumps(
                                {
                                    "source": "opencode.db/" + table,
                                    "record_id": row.get("id"),
                                    "kind": "reference_only_not_authoritative",
                                    "fingerprint": hashlib.sha256(
                                        raw.encode()
                                    ).hexdigest(),
                                }
                            )
                        )
                    continue
                tokens = obj.get("tokens", {})
                safe_tokens = (
                    {
                        k: v
                        for k, v in tokens.items()
                        if k in ("input", "output", "reasoning", "total")
                        and type(v) in (int, float)
                    }
                    if isinstance(tokens, dict)
                    else {}
                )
                cache = tokens.get("cache", {}) if isinstance(tokens, dict) else {}
                if isinstance(cache, dict):
                    safe_tokens["cache"] = {
                        k: v
                        for k, v in cache.items()
                        if k in ("read", "write") and type(v) in (int, float)
                    }
                print(
                    json.dumps(
                        {
                            "source": "opencode.db/" + table,
                            **row,
                            "kind": kind,
                            "model": obj.get("modelID")
                            if obj.get("modelID")
                            in ("gpt-6-astra", "gpt-5.6-sol", "gpt-5.4", "grok-4.6")
                            else None,
                            "has_error": bool(obj.get("error")),
                            "error_category": obj.get("error", {}).get("name")
                            if isinstance(obj.get("error"), dict)
                            and obj["error"].get("name")
                            in (
                                "MessageAbortedError",
                                "APIError",
                                "UnknownError",
                                "ContextOverflowError",
                                "ProviderAuthError",
                            )
                            else None,
                            "tokens": safe_tokens,
                            "finished": obj.get("finish")
                            if obj.get("finish")
                            in ("stop", "tool-calls", "error", "length")
                            else None,
                            **safe_summary(raw),
                        }
                    )
                )
    finally:
        connection.close()
    original = snapshot(ORIGINAL)
    print(
        json.dumps(
            {
                "original_reserved_cents": original["wallet"]["reserved_cents"],
                "original_hold_count": len(original["holds"]),
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Inspection stopped:", type(exc).__name__)
        raise SystemExit(1)
