from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict
from pydantic import Field


TOPUP_PACKAGES = {
    "starter_10": 1000,
    "starter_25": 2500,
    "starter_50": 5000,
    "starter_100": 10000,
    "starter_500": 50000,
    "starter_1000": 100000,
}


class CreateTopupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    package_id: str = Field(min_length=1, max_length=40)


class TopupResult(BaseModel):
    topup_id: str | None = None
    wallet_id: str | None = None
    balance_after_cents: int | None = None
    transaction_id: str | None = None
    already_processed: bool = False


def resolve_package_value_usd_cents(package_id: str) -> int:
    try:
        return TOPUP_PACKAGES[package_id]
    except KeyError as exc:
        raise ValueError("invalid_package_id") from exc


def convert_usd_cents_to_inr_minor_units(usd_cents: int, usd_to_inr_rate: str) -> int:
    value = (
        (Decimal(usd_cents) / Decimal("100"))
        * Decimal(usd_to_inr_rate)
        * Decimal("100")
    )
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
