from dataclasses import dataclass
import json
import logging
import httpx

from fastapi import status

from app.core.config import settings
from app.core.errors import OpenAIAPIError
from app.core.ids import create_request_id
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.repositories.profiles import fetch_profile
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.wallets import fetch_wallet
from app.repositories.reservations import reserve_usage, release_unconsumed_usage
from app.services.api_keys import ApiKeyServiceError
from app.services.api_keys import authenticate_api_key
from app.services.api_keys import touch_api_key_last_used
from app.services.models import ModelCatalogError
from app.services.models import get_model_by_slug
from app.services.rate_limit import acquire_concurrency_slot
from app.services.rate_limit import check_api_rate_limit
from app.services.rate_limit import release_concurrency_slot
from app.services.usage_records import preflight_spending_details

logger = logging.getLogger("aiforenza.balance")


async def release_rejected_request(
    authz: "AuthorizedAPIRequest", exc: Exception
) -> None:
    """Only known no-inference failures release holds; never release on timeout/5xx."""
    cause: BaseException | None = exc
    reason = None
    while cause is not None:
        if isinstance(cause, httpx.HTTPStatusError) and cause.response.status_code in (
            400,
            401,
            403,
            404,
            422,
            429,
        ):
            reason = "provider_rejected"
            break
        if isinstance(
            cause, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
        ):
            reason = "provider_not_connected"
            break
        cause = cause.__cause__
    if reason is not None:
        await release_unconsumed_usage(
            authz.request_id, authz.api_key["user_id"], authz.api_key["id"], reason
        )


@dataclass
class AuthorizedAPIRequest:
    request_id: str
    api_key: dict
    user: dict
    model: CatalogModel
    wallet: dict
    estimated_charge_cents: int


def _invalid_api_key() -> OpenAIAPIError:
    return OpenAIAPIError(
        "Invalid API key.",
        error_type="invalid_request_error",
        code="invalid_api_key",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def validate_request_size(raw_body: bytes, request: ChatCompletionRequest) -> None:
    if len(raw_body) > settings.api_max_request_bytes:
        raise OpenAIAPIError(
            "Request body is too large.",
            error_type="invalid_request_error",
            code="request_too_large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    if len(request.messages) > settings.api_max_messages:
        raise OpenAIAPIError(
            "Too many messages supplied.",
            error_type="invalid_request_error",
            code="request_too_large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


async def authorize_api_request(
    *,
    authorization: str | None,
    request: ChatCompletionRequest,
    raw_body: bytes,
    request_id: str | None = None,
) -> AuthorizedAPIRequest:
    validate_request_size(raw_body, request)
    request_id = request_id or create_request_id()

    if not authorization or not authorization.startswith("Bearer "):
        raise _invalid_api_key()

    plaintext_key = authorization.removeprefix("Bearer ").strip()
    if not plaintext_key:
        raise _invalid_api_key()

    try:
        api_key = await authenticate_api_key(plaintext_key)
    except ApiKeyServiceError as exc:
        raise OpenAIAPIError(
            "API key validation temporarily unavailable.",
            error_type="api_error",
            code="api_key_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if api_key is None:
        raise _invalid_api_key()

    try:
        profile = await fetch_profile(api_key["user_id"])
        wallet = await fetch_wallet(api_key["user_id"])
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            "Account validation temporarily unavailable.",
            error_type="api_error",
            code="account_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if profile is None or wallet is None:
        raise OpenAIAPIError(
            "User is not authorized to use the API.",
            error_type="invalid_request_error",
            code="user_inactive",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    check_api_rate_limit(user_id=api_key["user_id"], api_key_id=api_key["id"])
    acquire_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])

    try:
        model = await get_model_by_slug(request.model)
    except ModelCatalogError as exc:
        release_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])
        raise OpenAIAPIError(
            "Model catalog temporarily unavailable.",
            error_type="api_error",
            code="model_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if model is None:
        release_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])
        raise OpenAIAPIError(
            f"Model '{request.model}' not found.",
            error_type="invalid_request_error",
            code="model_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        spending = preflight_spending_details(request, model)
        estimated_charge_cents = spending["customer_charge_cents"]
    except BaseException:
        release_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])
        raise
    balance_cents = int(wallet.get("balance_cents", 0) or 0)
    available_cents = int(wallet.get("available_balance_cents", balance_cents) or 0)
    if wallet.get("currency", "USD") != "USD":
        release_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])
        raise OpenAIAPIError(
            "Wallet currency configuration is invalid.",
            error_type="api_error",
            code="wallet_currency_invalid",
            status_code=503,
        )
    decision = {
        "request_id": request_id,
        "user_id": api_key["user_id"],
        "api_key_id": api_key["id"],
        "wallet_id": wallet.get("id"),
        "currency": wallet.get("currency", "USD"),
        "wallet_balance_cents": balance_cents,
        "reserved_cents": wallet.get("reserved_cents", 0),
        "available_balance_cents": available_cents,
        "model": model.slug,
        **spending,
    }
    if estimated_charge_cents > available_cents or available_cents <= 0:
        logger.warning(json.dumps({**decision, "comparison": "rejected_preflight"}))
        release_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])
        raise OpenAIAPIError(
            "Insufficient balance. Please add funds to continue.",
            error_type="insufficient_balance",
            code="insufficient_balance",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )

    try:
        await touch_api_key_last_used(api_key["id"])
        await reserve_usage(
            request_id,
            api_key["user_id"],
            api_key["id"],
            model.id,
            estimated_charge_cents,
        )
    except BaseException as exc:
        release_concurrency_slot(user_id=api_key["user_id"], api_key_id=api_key["id"])
        if isinstance(exc, SupabaseRepositoryError):
            insufficient = "insufficient_balance" in str(exc)
            logger.warning(
                json.dumps(
                    {
                        **decision,
                        "comparison": "rejected_atomic_reservation"
                        if insufficient
                        else "reservation_unavailable",
                    }
                )
            )
            raise OpenAIAPIError(
                "Insufficient balance. Please add funds to continue."
                if insufficient
                else "Wallet authorization unavailable.",
                error_type="insufficient_balance" if insufficient else "api_error",
                code="insufficient_balance"
                if insufficient
                else "wallet_authorization_failed",
                status_code=402 if insufficient else 503,
            ) from exc
        raise

    logger.info(json.dumps({**decision, "comparison": "reserved"}))
    return AuthorizedAPIRequest(
        request_id=request_id,
        api_key=api_key,
        user=profile,
        model=model,
        wallet=wallet,
        estimated_charge_cents=estimated_charge_cents,
    )


def release_authorized_request(authz: AuthorizedAPIRequest) -> None:
    release_concurrency_slot(
        user_id=authz.api_key["user_id"], api_key_id=authz.api_key["id"]
    )
