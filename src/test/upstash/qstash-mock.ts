/**
 * @fileoverview Mock implementation of Upstash QStash for testing.
 *
 * Provides Client and Receiver mocks with message tracking for assertions.
 * Compatible with vi.doMock() for thread-safe testing with --pool=threads.
 */

// Types matching official @upstash/qstash API
// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
export type QStashPublishOptions = {
  url: string;
  body: unknown;
  headers?: Record<string, string>;
  retries?: number;
  delay?: number;
  deduplicationId?: string;
  callback?: string;
};

// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
export type QStashPublishResult = {
  messageId: string;
  url?: string;
  scheduled?: boolean;
};

// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
export type QStashMessage = QStashPublishOptions & {
  publishedAt: number;
  messageId: string;
};

// Shared state for message tracking
const publishedMessages: QStashMessage[] = [];
let verifyOutcome: boolean | Error = true;
let messageCounter = 0;

/**
 * Mock QStash Client for testing.
 * Tracks all published messages for test assertions.
 */
// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash Client class
export class QStashClientMock {
  // biome-ignore lint/complexity/noUselessConstructor: maintains API compatibility with @upstash/qstash Client
  constructor(_opts: { token: string; enableTelemetry?: boolean }) {
    // Constructor matches @upstash/qstash Client signature for compatibility
  }

  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash method name
  publishJSON(opts: QStashPublishOptions): Promise<QStashPublishResult> {
    messageCounter += 1;
    const messageId = `qstash-mock-${messageCounter}`;
    publishedMessages.push({ ...opts, messageId, publishedAt: Date.now() });
    return Promise.resolve({
      messageId,
      scheduled: (opts.delay ?? 0) > 0,
      url: opts.url,
    });
  }
}

/**
 * Mock QStash Receiver for testing signature verification.
 * Default behavior returns true; use forceVerifyOutcome() to control.
 */
// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash Receiver class
export class QStashReceiverMock {
  // biome-ignore lint/complexity/noUselessConstructor: maintains API compatibility with @upstash/qstash Receiver
  constructor(_opts: { currentSigningKey: string; nextSigningKey: string }) {
    // Constructor matches @upstash/qstash Receiver signature for compatibility
  }

  verify(_opts: {
    signature: string;
    body: string;
    url?: string;
    clockTolerance?: number;
  }): Promise<boolean> {
    if (verifyOutcome instanceof Error) return Promise.reject(verifyOutcome);
    return Promise.resolve(verifyOutcome);
  }
}

/**
 * Get all messages published via QStashClientMock.publishJSON().
 * Returns a copy to prevent mutation.
 */
export function getPublishedMessages(): QStashMessage[] {
  return [...publishedMessages];
}

/**
 * Force QStash signature verification outcome.
 * @param outcome - true/false for verify result, or Error to throw
 */
export function forceVerifyOutcome(outcome: boolean | Error): void {
  verifyOutcome = outcome;
}

/**
 * Reset all QStash mock state between tests.
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function resetQStashMock(): void {
  publishedMessages.length = 0;
  verifyOutcome = true;
  messageCounter = 0;
}

/**
 * QStash mock module type for vi.doMock registration.
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export type QStashMockModule = {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash export
  Client: typeof QStashClientMock;
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash export
  Receiver: typeof QStashReceiverMock;
  __reset: () => void;
  __getMessages: () => QStashMessage[];
  __forceVerify: (outcome: boolean | Error) => void;
};

/**
 * Create QStash mock module for vi.doMock() registration.
 *
 * @example
 * ```ts
 * const qstash = createQStashMock();
 * vi.doMock("@upstash/qstash", () => ({
 *   Client: qstash.Client,
 *   Receiver: qstash.Receiver,
 * }));
 *
 * beforeEach(() => qstash.__reset());
 * ```
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function createQStashMock(): QStashMockModule {
  return {
    __forceVerify: forceVerifyOutcome,
    __getMessages: getPublishedMessages,
    __reset: resetQStashMock,
    // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash export
    Client: QStashClientMock,
    // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash export
    Receiver: QStashReceiverMock,
  };
}
