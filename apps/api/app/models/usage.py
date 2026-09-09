from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class UsageMetrics(BaseModel):
    input_tokens: int = Field(ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)
    cached_input_tokens: int = Field(default=0, ge=0, strict=True)

    @model_validator(mode="after")
    def validate_cached_tokens(self):
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("Cached input cannot exceed total input tokens")
        return self


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
