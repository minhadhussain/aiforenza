import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.config import settings
from app.core.errors import OpenAIAPIError
from app.services import stripe_payments as payments


def test_real_stripe_signature_verification(monkeypatch):
    secret = "test-signing-fixture-not-a-credential"
    monkeypatch.setattr(settings, "stripe_webhook_secret", secret)
    timestamp = int(time.time())
    body = json.dumps(
        {
            "id": "evt_fixture",
            "object": "event",
            "type": "payment_intent.created",
            "data": {"object": {}},
        }
    ).encode()
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    signature = f"t={timestamp},v1={digest}"
    assert payments.verify_webhook_signature(body, signature).id == "evt_fixture"
    with pytest.raises(OpenAIAPIError) as error:
        payments.verify_webhook_signature(body + b" ", signature)
    assert error.value.status_code == 400
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    with pytest.raises(OpenAIAPIError) as error:
        payments.verify_webhook_signature(body, signature)
    assert error.value.status_code == 503


@pytest.mark.parametrize(
    "bad_field,value",
    [
        ("payment_status", "unpaid"),
        ("mode", "subscription"),
        ("status", "open"),
        ("amount_total", 2500),
        ("currency", "eur"),
        ("id", "cs_wrong"),
        ("client_reference_id", "wrong-user"),
        ("livemode", True),
    ],
)
def test_unpaid_or_mismatched_checkout_cannot_credit(monkeypatch, bad_field, value):
    topup_id = str(uuid4())
    data = {
        "id": "cs_fixture",
        "mode": "payment",
        "status": "complete",
        "payment_status": "paid",
        "livemode": False,
        "payment_intent": "pi_fixture",
        "client_reference_id": "user",
        "amount_total": 83500,
        "currency": "inr",
        "metadata": {
            "topup_id": topup_id,
            "user_id": "user",
            "package_id": "starter_10",
            "package_value_usd_cents": "1000",
            "stripe_amount_inr": "83500",
        },
    }
    data[bad_field] = value
    monkeypatch.setattr(
        payments,
        "fetch_topup_by_id",
        AsyncMock(
            return_value={
                "id": topup_id,
                "user_id": "user",
                "stripe_checkout_session_id": "cs_fixture",
                "amount_cents": 1000,
                "currency": "USD",
                "package_id": "starter_10",
                "package_value_usd_cents": 1000,
                "stripe_amount_inr": 83500,
                "stripe_currency": "INR",
            }
        ),
    )
    credit = AsyncMock()
    monkeypatch.setattr(payments, "complete_topup_record", credit)
    with pytest.raises(OpenAIAPIError):
        asyncio.run(
            payments.handle_checkout_completed(
                SimpleNamespace(id="evt_fixture", data={"object": data})
            )
        )
    credit.assert_not_called()
