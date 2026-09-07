from decimal import Decimal

from pydantic import BaseModel


class UsageMetrics(BaseModel):
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


class UsageChargeResult(BaseModel):
    wallet_id: str
    balance_after_cents: int
    transaction_id: str | None = None
    usage_record_id: str


class CustomerCharge(BaseModel):
    cents: int
    input_component: Decimal
    output_component: Decimal
    cached_component: Decimal
