# Tenacity-Only Resilience

This document describes the final TripSage resilience approach based on the
Tenacity library. We removed custom wrappers and the circuit breaker module to
reduce complexity and standardize on proven, composable retry primitives.

## Guidelines

- Use shared policies from `tripsage_core/infrastructure/retry_policies.py`.
- Prefer jittered exponential backoff: `wait_random_exponential(min=1, max=10)`.
- Always cap attempts and total time: `stop_after_attempt(N)`, `stop_after_delay(<=30)`.
- Use precise exception predicates (e.g., httpx timeouts/connect errors).
- Set `reraise=True` to surface the final exception.
- Integrate logging with `before_sleep_log(logger, WARNING, exc_info=True)`.
- Add OTEL spans via `before_sleep_otel` only on important dependencies.

## Policies

- `httpx_async_retry(attempts=3, max_delay=10.0, include_status_error=False)`
- `httpx_block_retry(...)` for block-style AsyncRetrying
- `generic_retry(...)` for synchronous calls

## Usage Examples

- Decorator style (async):
  `@httpx_async_retry(attempts=3, max_delay=10.0)`
- Block style (async):
  `async for attempt in httpx_block_retry(...): with attempt: ...`

## Do/Don’t

- Do not retry non-idempotent operations unless explicitly safe.
- Do not catch broad `Exception` at call sites; rely on Tenacity predicates.
- Do use client timeouts in addition to retry budgets.

## Removed Components

- Custom `retry_on_failure` decorator.
- `tripsage_core.infrastructure.resilience` circuit breaker module.
