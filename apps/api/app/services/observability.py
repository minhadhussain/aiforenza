from __future__ import annotations

from typing import Any

from app.core.config import settings


def init_sentry() -> None:
    if not settings.sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        environment=settings.api_env,
        traces_sample_rate=0.0,
    )


def init_posthog() -> None:
    if not settings.posthog_key or not settings.posthog_host:
        return

    import posthog

    posthog.api_key = settings.posthog_key
    posthog.host = settings.posthog_host
    posthog.disable_geoip = True


def capture_event(distinct_id: str, event: str, properties: dict[str, Any] | None = None) -> None:
    if not settings.posthog_key or not settings.posthog_host:
        return

    try:
        import posthog

        posthog.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception:
        return
