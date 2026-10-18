import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx


# Keep connections for the API's lifetime, without sharing an async transport
# across event loops (CLI tools and TestClient also call these repositories).
_clients: dict[asyncio.AbstractEventLoop, httpx.AsyncClient] = {}


@asynccontextmanager
async def supabase_http_lifespan() -> AsyncIterator[None]:
    loop = asyncio.get_running_loop()
    async with httpx.AsyncClient(timeout=10.0) as client:
        _clients[loop] = client
        try:
            yield
        finally:
            _clients.pop(loop, None)


@asynccontextmanager
async def supabase_http_client() -> AsyncIterator[httpx.AsyncClient]:
    client = _clients.get(asyncio.get_running_loop())
    if client is not None:
        # Credentials stay on each request, never on the pooled client.
        yield client
    else:
        # One-off scripts have no ASGI lifespan to close a persistent pool.
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client
