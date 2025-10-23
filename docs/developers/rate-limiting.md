# Rate Limiting (SlowAPI + aiolimiter)

This document describes TripSage's standardized rate limiting:

- Inbound (server): SlowAPI for FastAPI with limits async storage.
- Outbound (clients): aiolimiter per-host throttling with 429 backoff.

## Architecture

```mermaid
graph TB
    A[Request] --> B[SlowAPIMiddleware]
    B --> C[Limiter (SlowAPI)]
    C --> D{Storage}
    D -->|async+redis(s)://| E[limits async backend]
    D -->|memory://| E
    E --> F[429 or Allow + X-RateLimit-* headers]
```

## Configuration (environment)

- `DEFAULT_RATE_LIMIT` (e.g., `120/minute`) global default.
- `RATE_LIMIT_STORAGE_URI` explicit URI (e.g., `async+rediss://:PASSWORD@host:port/0`).
- Detection order for storage when unset:
  1. `settings.redis_url` (supports `redis://` or `rediss://`)
  2. `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TLS_URL`, `REDIS_URL`, `VALKEY_URL`, `DRAGONFLY_URL`
     (auto-mapped to `async+redis://` / `async+rediss://`)
- `LIMITS_IMPL=redispy|coredis` (default `redispy`).

Upstash REST (`UPSTASH_REDIS_REST_URL`) is not compatible with limits; provision a TCP/TLS endpoint.

## Usage (inbound)

- Limiter is installed globally in `tripsage/api/limiting.py` via `install_rate_limiting()`.
- Per-route limits via `@limiter.limit("N/minute")`. Ensure the endpoint has `request: Request, response: Response`.
- Exempt with `@limiter.exempt` (e.g., for health endpoints).

Example:

```python
from fastapi import APIRouter, Request, Response
from tripsage.api.limiting import limiter

router = APIRouter()

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, response: Response):
    return {"ok": True}
```

## Outbound throttling

All outbound HTTP must use `tripsage_core.utils.outbound.request_with_backoff`:

- One `AsyncLimiter` per host
- 429: honor `Retry-After`, else random exponential backoff

Environment:

- `OUTBOUND_QPM_DEFAULT` (default 60)
- Per-host overrides: `OUTBOUND_QPM__API_OPENAI_COM=120`

## Headers and behavior

- Headers enabled by default: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- On 429, `Retry-After` is set by SlowAPI.

## Testing

- Unit tests use `memory://` storage for speed.
- Inbound test: `tests/unit/api/test_rate_limit_inbound.py` (429 on 4th call).
- Outbound tests: `tests/unit/infrastructure/test_http_outbound_limiter.py` (MockTransport).

## Migration notes

- Removed custom `RateLimitMiddleware` and Dragonfly-based algorithms.
- Frontend rate limiting removed; backend is the single source of truth.
- See ADR: `docs/adrs/adr-0012-slowapi-aiolimiter-migration.md`.
