# ADR-0011: Adopt Tenacity-Only Resilience, Remove Circuit Breaker

**Date**: 2025-10-21

## Status

Accepted

## Context

The codebase contained a custom retry wrapper and a circuit breaker module with
state management, registries, and analytics. This added cognitive load and
maintenance without clear product value versus standard retries + rate limiting.

## Decision

Adopt Tenacity 9.x as the sole resilience primitive and remove the circuit
breaker module and the bespoke retry decorator. Provide thin, typed policy
factories to standardize retry behavior across services.

## Consequences

### Positive

- Simpler resilience story; fewer abstractions to learn and maintain.
- Uniform jittered backoff and budgets; improved observability via logging/OTEL.
- No breaker state; rely on budgets, timeouts, and rate limiting to avoid storms.

### Negative

### Neutral

## Implementation

- Added `tripsage_core/infrastructure/retry_policies.py`.
- Removed `retry_on_failure` and `resilience/circuit_breaker`.
- Migrated external API services to Tenacity policies.
- Updated/removed tests tied to removed modules.

## Alternatives Considered

### Stay with custom retry wrapper

- Added `tripsage_core/infrastructure/retry_policies.py`.
- Removed `retry_on_failure` and `resilience/circuit_breaker`.
- Migrated external API services to Tenacity policies.
- Updated/removed tests tied to removed modules.
