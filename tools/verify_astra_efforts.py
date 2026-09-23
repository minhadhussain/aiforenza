"""Real OpenCode --variant and plain streaming checks, with ledger reconciliation.

Uses the existing AI Forenza global provider/key. Only the synthetic fixture is
available for read-only tool testing. Never prints client output, prompts or keys.
"""

import argparse
import asyncio
import json
import subprocess
import re
from pathlib import Path

import httpx
from configure_opencode_global import executable, global_path
from trace_astra_compat import client_env, EFFORTS
from opencode_live_test import ROOT, state, snapshot, select, require
from app.repositories.models import fetch_model_by_slug
from app.services.api_keys import authenticate_api_key
from app.services.pricing import calculate_pricing_breakdown
from app.models.usage import UsageMetrics

STAGE = "configuration"


def main():
    global STAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--models", nargs="+", default=["gpt-6-astra"])
    parser.add_argument("--efforts", nargs="+", choices=EFFORTS, default=list(EFFORTS))
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output-tokens", type=int, default=4096)
    args = parser.parse_args()
    config = json.loads(global_path().read_text(encoding="utf-8"))
    provider = config["provider"]["aiforenza"]
    require(provider["npm"] == "@ai-sdk/openai-compatible", "Provider SDK changed")
    require(set(provider["models"]["gpt-6-astra"]["variants"]) == set(EFFORTS), "Variant definitions missing")
    api_key = provider["options"]["apiKey"]
    key = asyncio.run(authenticate_api_key(api_key))
    require(key and key["user_id"] == state()["user_id"], "Verification must use the existing funded test account")
    user = key["user_id"]
    before = snapshot(user)
    require(before["wallet"]["available_balance_cents"] >= 500, "Insufficient test balance")
    seen = {r["request_id"] for r in select("usage_records", user)}
    report = []
    prompts = {
        "low": "Read astra_effort_check.py using the read tool. Identify its termination bug in one sentence. Do not edit files.",
        "medium": "Read astra_effort_check.py using the read tool. Explain the termination bug and give two boundary test cases. Keep the answer under 100 words. Do not edit files.",
        "high": "Read astra_effort_check.py using the read tool. State a loop invariant, derive the minimal correction, and prove termination using a decreasing measure. Under 150 words; do not edit files.",
        "xhigh": "Read astra_effort_check.py using the read tool. Derive a duplicate-aware lower-bound search from it, reason through empty/all-equal/missing-target cases and state its invariant. Under 180 words; do not edit files.",
        "max": "Read astra_effort_check.py using the read tool. Plan its migration into a crash-recoverable sorted-index search service: derive a terminating search, concurrent snapshot semantics, a staged rollout and correctness checks under crash/retry. Prioritize invariants and give a compact multi-step plan under 200 words. Do not edit files.",
    }
    for slug in args.models:
        model = asyncio.run(fetch_model_by_slug(slug))
        efforts = args.efforts if slug == "gpt-6-astra" else (None,)
        for effort in efforts:
            STAGE = f"{slug}/{effort or 'existing-default'}"
            start = snapshot(user)
            if args.plain:
                with httpx.Client(timeout=args.timeout) as client:
                    body = {"model": slug, "messages": [{"role": "user", "content": "Give one sentence explaining binary search termination."}], "max_tokens": 1024, "stream": True}
                    if effort:
                        body["reasoning_effort"] = effort
                    result = client.post(provider["options"]["baseURL"] + "/chat/completions", headers={"Authorization": "Bearer " + api_key}, json=body)
                require(result.status_code == 200 and "data: [DONE]" in result.text and '"error"' not in result.text, "Plain streaming failed; inspect retained holds")
                events = []
                used_tools = False
            else:
                env = client_env()
                env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"share": "disabled", "agent": {"title": {"disable": True}}, "permission": {"edit": "deny", "bash": "deny", "task": "deny", "read": "allow", "glob": "allow", "grep": "allow", "list": "allow", "webfetch": "deny", "websearch": "deny"}, "provider": {"aiforenza": {"options": {"timeout": args.timeout * 1000, "chunkTimeout": args.timeout * 1000}, "models": {slug: {"limit": {**provider["models"][slug]["limit"], "output": args.output_tokens}}}}}})
                command = [str(executable()), "run", "--print-logs", "--pure", "--format", "json", "--model", "aiforenza/" + slug, "--title", "Astra effort integration check"]
                if effort:
                    command += ["--variant", effort]
                command.append(prompts[effort or "low"])
                result = subprocess.run(command, cwd=ROOT / "tools/fixtures", env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout)
                events = []
                for line in result.stdout.splitlines():
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict):
                            events.append(item)
                    except ValueError:
                        pass
                used_tools = any(e.get("type") == "tool_use" and e.get("part", {}).get("tool") == "read" and e.get("part", {}).get("state", {}).get("status") == "completed" for e in events)
                print(json.dumps({"client_exit": result.returncode, "event_types": [e.get("type") for e in events], "finish_reasons": [e.get("part", {}).get("reason") for e in events if e.get("type") == "step_finish"], "exception_categories": sorted(set(re.findall(r"\b[A-Z][A-Za-z]+(?:Error|Exception)\b", result.stderr))), "error_names": [e.get("error", {}).get("name") for e in events if e.get("type") == "error"]}), flush=True)
                require(result.returncode == 0 and any(e.get("type") == "text" for e in events) and not any(e.get("type") == "error" for e in events), "OpenCode request failed; inspect safe provider diagnostics")
                require(used_tools, "OpenCode did not complete the requested read-tool flow")
            rows = [r for r in select("usage_records", user) if r["request_id"] not in seen]
            require(bool(rows), "Missing completed usage")
            after = snapshot(user)
            traces = []
            for line in args.logs.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    event = json.loads(line)
                    if event.get("request_id") in {r["request_id"] for r in rows}:
                        traces.append(event)
                except (ValueError, AttributeError):
                    pass
            charge = 0
            for row in rows:
                expected = calculate_pricing_breakdown(model, UsageMetrics(input_tokens=row["input_tokens"], output_tokens=row["output_tokens"], cached_input_tokens=row["cached_input_tokens"]), billing_source=key.get("billing_source", "PAID"))
                require(row["customer_charge_cents"] == expected.customer_charge_cents and row["reference_charge_cents"] == expected.reference_charge_cents, "Usage price mismatch")
                ledger = [t for t in after["transactions"] if t["reference_id"] == "usage:" + row["request_id"]]
                require(len(ledger) == 1 and ledger[0]["amount_cents"] == -expected.customer_charge_cents, "Ledger mismatch")
                replies = [t for t in traces if t.get("request_id") == row["request_id"] and t.get("event") == "provider_response"]
                require(len(replies) == 1 and replies[0]["provider_status"] == 200, "Missing real provider 200 evidence")
                if effort:
                    require(replies[0]["reasoning_effort"] == effort, "Provider effort mismatch")
                charge += row["customer_charge_cents"]
                seen.add(row["request_id"])
            require(start["wallet"]["balance_cents"] - after["wallet"]["balance_cents"] == charge, "Wallet delta mismatch")
            require(after["holds"] == before["holds"], "New unresolved hold or pre-existing hold changed")
            record = {"model": slug, "effort": effort, "mode": "plain_stream" if args.plain else "opencode", "tool_read_completed": used_tools, "requests": [{"request_id": r["request_id"], "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"], "reference_cents": r["reference_charge_cents"], "customer_cents": r["customer_charge_cents"]} for r in rows], "provider_status": 200, "provider_apis": sorted({e.get("provider_api") for e in traces if e.get("event") == "provider_response"}), "charge_cents": charge, "remaining_cents": after["wallet"]["balance_cents"], "existing_holds_preserved": True}
            report.append(record)
            print(json.dumps(record), flush=True)
    print(json.dumps({"verified_flows": len(report), "paid_discount_preserved": True, "actual_usage_billing": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Stage:", STAGE)
        print(str(exc) if type(exc) is RuntimeError else "Verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
