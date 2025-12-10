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

/**
 * QStash mock module type for vi.doMock registration.
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
type QStashClientConstructor = new (opts: {
  token: string;
  enableTelemetry?: boolean;
}) => {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
  publishJSON: (opts: QStashPublishOptions) => Promise<QStashPublishResult>;
};

// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
type QStashReceiverConstructor = new (opts: {
  currentSigningKey: string;
  nextSigningKey: string;
}) => {
  verify: (opts: {
    signature: string;
    body: string;
    url?: string;
    clockTolerance?: number;
  }) => Promise<boolean>;
};

// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
export type QStashMockModule = {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash export
  Client: QStashClientConstructor;
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash export
  Receiver: QStashReceiverConstructor;
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
  // Shared state for this mock instance
  const publishedMessages: QStashMessage[] = [];
  let verifyOutcome: boolean | Error = true;
  let messageCounter = 0;

  // Mock QStash Client for testing (per-instance state)
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash Client class
  class QStashClientMock {
    private readonly token: string;

    private readonly enableTelemetry?: boolean;

    constructor(opts: { token: string; enableTelemetry?: boolean }) {
      this.token = opts.token;
      this.enableTelemetry = opts.enableTelemetry;
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

  // Mock QStash Receiver for testing signature verification (per-instance state)
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash Receiver class
  class QStashReceiverMock {
    private readonly currentSigningKey: string;

    private readonly nextSigningKey: string;

    constructor(opts: { currentSigningKey: string; nextSigningKey: string }) {
      this.currentSigningKey = opts.currentSigningKey;
      this.nextSigningKey = opts.nextSigningKey;
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

  const getPublishedMessages = (): QStashMessage[] => [...publishedMessages];

  const forceVerifyOutcome = (outcome: boolean | Error): void => {
    verifyOutcome = outcome;
  };

  // biome-ignore lint/style/useNamingConvention: mirrors QStash naming
  const resetQStashMock = (): void => {
    publishedMessages.length = 0;
    verifyOutcome = true;
    messageCounter = 0;
  };

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
