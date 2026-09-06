from app.repositories.wallets import build_wallet_summary


def test_build_wallet_summary_without_wallet() -> None:
    summary = build_wallet_summary(None, [])

    assert summary["wallet"] is None
    assert summary["metrics"]["current_balance_cents"] == 0
    assert summary["metrics"]["trial_credit_granted"] is False


def test_build_wallet_summary_detects_trial_credit() -> None:
    wallet = {
        "id": "wallet-1",
        "balance_cents": 500,
        "currency": "USD",
    }
    transactions = [
        {
            "id": "tx-1",
            "type": "FREE_TRIAL",
            "amount_cents": 500,
            "balance_after_cents": 500,
            "description": "Initial $5.00 trial credit",
            "reference_id": "signup:user-1",
            "created_at": "2026-09-07T00:00:00Z",
        }
    ]

    summary = build_wallet_summary(wallet, transactions)

    assert summary["wallet"]["id"] == "wallet-1"
    assert summary["metrics"]["current_balance_cents"] == 500
    assert summary["metrics"]["trial_credit_granted"] is True
