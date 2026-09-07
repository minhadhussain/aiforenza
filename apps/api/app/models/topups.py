from pydantic import BaseModel
from pydantic import Field


class CreateTopupRequest(BaseModel):
    amount_cents: int = Field(gt=0)


class TopupResult(BaseModel):
    topup_id: str | None = None
    wallet_id: str | None = None
    balance_after_cents: int | None = None
    transaction_id: str | None = None
    already_processed: bool = False
