"""Read-only historical reconciliation report. No secrets or prompt text printed.

Correlates exact request IDs, never assumes that age or a generic 502 means free.
"""

import asyncio
import argparse
import hashlib
import json
import re
import sqlite3
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


def safe_events(text):
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        headers = obj.get("responseHeaders", {})
        if not isinstance(headers, dict):
            continue
        rid = headers.get("x-request-id") or obj.get("request_id")
        if not isinstance(rid, str) or not re.fullmatch(r"req_[a-f0-9]{32}", rid):
            continue
        body = obj.get("responseBody", {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                body = {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        if not isinstance(error, dict):
            error = {}
        code = error.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,80}", code):
            code = None
        status = obj.get("statusCode")
        if type(status) is not int or not 100 <= status <= 599:
            status = None
        yield {
            "request_id": rid,
            "http_status": status,
            "code": code,
            "has_usage": isinstance(body, dict) and isinstance(body.get("usage"), dict),
            "fingerprint": hashlib.sha256(
                json.dumps(obj, sort_keys=True).encode()
            ).hexdigest(),
        }


def evidence_for(request_ids, *, root=ROOT, home=None):
    home = home or Path.home()
    evidence = {rid: [] for rid in request_ids}
    coverage = {
        "files_scanned": 0,
        "database_rows_matched": 0,
        "database_tables_scanned": [],
        "database_present": False,
    }
    sources = list((root / "apps/api").glob("*.log"))
    sources += list((home / ".local/share/opencode/log").glob("*.log"))
    sources += list((home / ".local/share/opencode/storage").rglob("*.json"))

    seen_evidence = set()

    def append(event):
        identity = (event["request_id"], event["source"], event["fingerprint"])
        if identity not in seen_evidence:
            seen_evidence.add(identity)
            evidence[event["request_id"]].append(event)

    def collect(text, source):
        matched = set(re.findall(r"req_[a-f0-9]{32}", text)) & evidence.keys()
        if not matched:
            return
        parsed = set()
        for event in safe_events(text):
            if event["request_id"] in matched:
                parsed.add(event["request_id"])
                append({**event, "source": source})
        for rid in matched - parsed:
            append(
                {
                    "request_id": rid,
                    "source": source,
                    "kind": "exact_id_reference_without_structured_outcome",
                    "fingerprint": hashlib.sha256(text.encode()).hexdigest(),
                }
            )

    for path in sources:
        text = path.read_text(encoding="utf-8", errors="replace")
        coverage["files_scanned"] += 1
        collect(text, path.name)
    db = home / ".local/share/opencode/opencode.db"
    if db.exists():
        coverage["database_present"] = True
        connection = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "select name from sqlite_master where type='table'"
                )
            }
            for table in ("message", "part"):
                if table not in tables:
                    continue
                columns = {
                    row[1] for row in connection.execute(f"pragma table_info({table})")
                }
                if "data" not in columns:
                    continue
                coverage["database_tables_scanned"].append(table)
                seen_rows = set()
                # Fetch only records that reference the exact held request IDs.
                for rid in request_ids:
                    for (data,) in connection.execute(
                        f"select data from {table} where data like ?",
                        ("%" + rid + "%",),
                    ):
                        fingerprint = hashlib.sha256(data.encode()).hexdigest()
                        if fingerprint in seen_rows:
                            continue
                        seen_rows.add(fingerprint)
                        coverage["database_rows_matched"] += 1
                        collect(data, "opencode.db/" + table)
        finally:
            connection.close()
    return evidence, coverage


async def inspect():
    keys = opencode_keys()
    if len(keys) != 1:
        raise RuntimeError("Expected one configured AI Forenza key")
    matches = await rest_select(
        "/rest/v1/api_keys",
        {"key_hash": "eq." + hash_api_key(keys[0]), "select": "id,user_id,revoked_at"},
    )
    if len(matches) != 1:
        raise RuntimeError("Key not identified")
    key = matches[0]
    holds = await rest_select(
        "/rest/v1/wallet_reservations",
        {
            "user_id": "eq." + key["user_id"],
            "select": "request_id,api_key_id,model_id,amount_cents,created_at",
            "order": "created_at.asc",
        },
    )
    evidence, coverage = evidence_for([item["request_id"] for item in holds])
    report = []
    for hold in holds:
        usage = await rest_select(
            "/rest/v1/usage_records",
            {
                "request_id": "eq." + hold["request_id"],
                "select": "id,user_id,api_key_id,model_id,input_tokens,output_tokens,customer_charge_cents,status",
            },
        )
        transactions = await rest_select(
            "/rest/v1/transactions",
            {
                "reference_id": "eq.usage:" + hold["request_id"],
                "select": "id,user_id,amount_cents,balance_after_cents",
            },
        )
        # A downstream error code is not authoritative evidence of upstream status.
        report.append(
            {
                **hold,
                "classification": "uncertain",
                "reason": (
                    "Recorded billing evidence requires manual ownership and settlement review"
                    if usage or transactions
                    else "Local references do not establish authoritative provider outcome"
                    if evidence[hold["request_id"]]
                    else "No exact-request outcome found in scanned local evidence"
                ),
                "usage_records": usage,
                "transactions": transactions,
                "evidence": evidence[hold["request_id"]],
                "action": "retain pending authoritative provider outcome",
            }
        )
    wallet = await fetch_wallet(key["user_id"])
    result = {
        "key_id": key["id"],
        "user_id": key["user_id"],
        "coverage": coverage,
        "evidence_limitations": (
            "Local references can include later audit transcripts, not original events. "
            "Neither those references nor downstream HTTP status prove upstream consumption. "
            "No automatic release or settlement is performed."
        ),
        "summary": {
            "outstanding_count": len(holds),
            "outstanding_cents": sum(hold["amount_cents"] for hold in holds),
            "released_count": 0,
            "settled_count": 0,
            "read_only": True,
        },
        "wallet": {
            k: wallet[k]
            for k in (
                "balance_cents",
                "reserved_cents",
                "available_balance_cents",
                "currency",
            )
        },
        "reservations": report,
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary", action="store_true", help="Omit individual evidence fingerprints"
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(inspect())
        if args.summary:
            for hold in result["reservations"]:
                evidence = hold.pop("evidence")
                hold["evidence_count"] = len(evidence)
                hold["downstream_statuses"] = sorted(
                    {
                        item["http_status"]
                        for item in evidence
                        if item.get("http_status") is not None
                    }
                )
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print("Reconciliation inspection failed:", type(exc).__name__)
        sys.exit(1)
