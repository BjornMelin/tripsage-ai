/**
 * @fileoverview Expedia Rapid provider adapter with retry/backoff and circuit breaker.
 *
 * Adds telemetry, bounded retries with jitter, and an in-memory circuit breaker on top
 * of {@link ExpediaClient}. All errors are normalized to {@link ProviderError} so
 * upstream callers can map failures consistently.
 */

import { ProviderError, type ProviderErrorCode } from "@domain/accommodations/errors";
import type {
  AccommodationProviderAdapter,
  ProviderContext,
} from "@domain/accommodations/providers/types";
import { ExpediaApiError, getExpediaClient } from "@domain/expedia/client";
import type {
  EpsCheckAvailabilityRequest,
  EpsCheckAvailabilityResponse,
  EpsCreateBookingRequest,
  EpsCreateBookingResponse,
  EpsPropertyDetailsResponse,
  EpsSearchRequest,
  EpsSearchResponse,
  RapidPriceCheckResponse,
} from "@schemas/expedia";
import { retryWithBackoff } from "@/lib/http/retry";
import { secureUuid } from "@/lib/security/random";
import { withTelemetrySpan } from "@/lib/telemetry/span";

type CircuitState = "closed" | "open" | "half_open";

type BreakerConfig = {
  failureThreshold: number;
  cooldownMs: number;
};

type RetryConfig = {
  attempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
};

type AdapterConfig = {
  breaker?: BreakerConfig;
  retry?: RetryConfig;
  timeoutMs?: number;
};

const DEFAULT_RETRYABLE_CODES = new Set([429, 408, 500, 502, 503, 504]);

class InMemoryCircuitBreaker {
  private state: CircuitState = "closed";
  private failures = 0;
  private openedAt = 0;

  constructor(private readonly config: BreakerConfig) {}

  canProceed(): boolean {
    if (this.state === "open") {
      const elapsed = Date.now() - this.openedAt;
      if (elapsed >= this.config.cooldownMs) {
        this.state = "half_open";
        return true;
      }
      return false;
    }
    return true;
  }

  recordSuccess(): void {
    this.state = "closed";
    this.failures = 0;
  }

  recordFailure(): void {
    this.failures += 1;
    if (this.failures >= this.config.failureThreshold) {
      this.state = "open";
      this.openedAt = Date.now();
    }
  }

  getState(): CircuitState {
    return this.state;
  }
}

export class ExpediaProviderAdapter implements AccommodationProviderAdapter {
  readonly name = "expedia" as const;

  private readonly breaker: InMemoryCircuitBreaker;
  private readonly retryable = DEFAULT_RETRYABLE_CODES;
  private readonly retryConfig: RetryConfig;
  private readonly timeoutMs: number;

  constructor(config?: AdapterConfig) {
    const breakerConfig: BreakerConfig = config?.breaker ?? {
      cooldownMs: 30_000,
      failureThreshold: 4,
    };
    this.breaker = new InMemoryCircuitBreaker(breakerConfig);
    this.retryConfig = config?.retry ?? {
      attempts: 3,
      baseDelayMs: 200,
      maxDelayMs: 1_000,
    };
    this.timeoutMs = config?.timeoutMs ?? 5_000;
  }

  /**
   * Searches availability via Rapid Shopping API with retry and circuit breaker.
   */
  searchAvailability(params: EpsSearchRequest, ctx?: ProviderContext) {
    return this.execute<EpsSearchResponse>("searchAvailability", ctx, () =>
      getExpediaClient().searchAvailability(params, this.buildContext(ctx))
    );
  }

  /**
   * Retrieves property content from Rapid Content API.
   */
  getPropertyDetails(
    params: { propertyId: string; language?: string },
    ctx?: ProviderContext
  ) {
    return this.execute<EpsPropertyDetailsResponse>("getPropertyDetails", ctx, () =>
      getExpediaClient().getPropertyDetails(
        { language: params.language, propertyId: params.propertyId },
        this.buildContext(ctx)
      )
    );
  }

  checkAvailability(params: EpsCheckAvailabilityRequest, ctx?: ProviderContext) {
    return this.execute<EpsCheckAvailabilityResponse>("checkAvailability", ctx, () =>
      getExpediaClient().checkAvailability(params, this.buildContext(ctx))
    );
  }

  /**
   * Checks price for a specific rate-token combination.
   */
  priceCheck(
    params: { propertyId: string; roomId: string; rateId: string; token: string },
    ctx?: ProviderContext
  ) {
    return this.execute<RapidPriceCheckResponse>("priceCheck", ctx, () =>
      getExpediaClient().priceCheck(params, this.buildContext(ctx))
    );
  }

  createBooking(params: EpsCreateBookingRequest, ctx?: ProviderContext) {
    return this.execute<EpsCreateBookingResponse>("createBooking", ctx, () =>
      getExpediaClient().createBooking(params, this.buildContext(ctx))
    );
  }

  /**
   * Wraps a provider call with telemetry, retry, and circuit breaker.
   */
  private execute<T>(
    operation: string,
    _ctx: ProviderContext | undefined,
    fn: () => Promise<T>
  ): Promise<
    | { ok: true; retries: number; value: T }
    | { error: ProviderError; ok: false; retries: number }
  > {
    return withTelemetrySpan(
      `provider.expedia.${operation}`,
      {
        attributes: {
          "provider.circuit_state": this.breaker.getState(),
          "provider.name": this.name,
          "provider.operation": operation,
        },
      },
      async (span) => {
        if (!this.breaker.canProceed()) {
          const error = new ProviderError("circuit_open", "expedia circuit open", {
            operation,
            provider: this.name,
          });
          span.recordException(error);
          return { error, ok: false, retries: 0 };
        }

        let retries = 0;
        try {
          const result = await retryWithBackoff(() => this.withTimeout(fn), {
            attempts: this.retryConfig.attempts,
            baseDelayMs: this.retryConfig.baseDelayMs,
            isRetryable: (error) => this.isRetryable(error),
            maxDelayMs: this.retryConfig.maxDelayMs,
            onRetry: ({ delayMs }) => {
              retries += 1;
              span.addEvent("provider.retry", {
                attempt: retries,
                delayMs,
              });
            },
          });
          this.breaker.recordSuccess();
          span.setAttribute("provider.retries", retries);
          span.setAttribute("provider.circuit_state", this.breaker.getState());
          return { ok: true, retries, value: result };
        } catch (error) {
          this.breaker.recordFailure();
          const providerError = this.normalizeError(error, operation);
          span.recordException(providerError);
          span.setAttribute("provider.circuit_state", this.breaker.getState());
          return { error: providerError, ok: false, retries };
        }
      }
    );
  }

  private buildContext(ctx?: ProviderContext) {
    return {
      customerIp: ctx?.clientIp,
      customerSessionId: ctx?.sessionId ?? ctx?.userId ?? secureUuid(),
      testScenario: ctx?.testScenario,
      userAgent: ctx?.userAgent,
    };
  }

  private isRetryable(error: unknown): boolean {
    if (error instanceof ExpediaApiError && error.statusCode) {
      return this.retryable.has(error.statusCode);
    }
    return false;
  }

  private normalizeError(error: unknown, operation: string): ProviderError {
    if (error instanceof ProviderError) return error;
    if (error instanceof ExpediaApiError) {
      const mapped = this.mapStatus(error.statusCode);
      return new ProviderError(mapped, error.message, {
        operation,
        provider: this.name,
        statusCode: error.statusCode,
      });
    }
    return new ProviderError("provider_failed", "expedia adapter error", {
      operation,
      provider: this.name,
    });
  }

  private mapStatus(status?: number): ProviderErrorCode {
    if (status === 401) return "unauthorized";
    if (status === 404) return "not_found";
    if (status === 429) return "rate_limited";
    if (status && status >= 500) return "provider_failed";
    return "provider_failed";
  }

  private async withTimeout<T>(fn: () => Promise<T>): Promise<T> {
    return await Promise.race([
      fn(),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("provider_timeout")), this.timeoutMs)
      ),
    ]);
  }
}
