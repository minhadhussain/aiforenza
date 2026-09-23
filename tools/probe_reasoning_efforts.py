"""Bounded Azure capability probes; prints only effort/status/model metadata."""

import asyncio
import json

import httpx
from opencode_live_test import require
from app.core.config import settings
from app.repositories.models import fetch_enabled_models


def main():
    catalog = {model.slug: model for model in asyncio.run(fetch_enabled_models())}
    require(settings.azure_endpoint and settings.azure_api_key, "Configured Azure provider required")
    with httpx.Client(timeout=120) as client:
        for slug in ("gpt-5.4", "gpt-5.6-sol"):
            for effort in (None, "none", "low", "medium", "high", "xhigh", "max"):
                payload = {"model": catalog[slug].provider_model_id, "input": "Reply OK.", "max_output_tokens": 128, "store": False}
                if effort is not None:
                    payload["reasoning"] = {"effort": effort}
                response = client.post(settings.azure_endpoint.rstrip("/") + "/responses", headers={"api-key": settings.azure_api_key}, json=payload)
                result = response.json()
                actual = (result.get("reasoning") or {}).get("effort")
                code = (result.get("error") or {}).get("code")
                print(json.dumps({"model": slug, "requested_effort": effort, "provider_status": response.status_code, "returned_effort": actual if actual in {"none", "low", "medium", "high", "xhigh", "max"} else None, "error_code": code if code in {"unsupported_value", "unsupported_parameter", "invalid_request_error"} else None}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Capability probe stopped: " + type(exc).__name__)
        raise SystemExit(1)
