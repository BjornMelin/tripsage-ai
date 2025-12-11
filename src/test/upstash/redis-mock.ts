/**
 * @fileoverview Mock implementation of Upstash Redis for testing.
 *
 * Provides a shared in-memory store for Redis operations, simulating Redis
 * behavior with TTL tracking and pipeline support.
 */

type StoredValue = {
  value: string;
  expiresAt?: number;
};

export type UpstashMemoryStore = Map<string, StoredValue>;

export function createUpstashMemoryStore(): UpstashMemoryStore {
  return new Map<string, StoredValue>();
}

export const sharedUpstashStore: UpstashMemoryStore = createUpstashMemoryStore();

function serialize(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function deserialize(raw: string | undefined): unknown {
  if (raw === undefined) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function isExpired(entry: StoredValue | undefined, now: number): boolean {
  return !!entry?.expiresAt && entry.expiresAt <= now;
}

function touch(
  store: UpstashMemoryStore,
  key: string,
  now: number
): StoredValue | undefined {
  const entry = store.get(key);
  if (isExpired(entry, now)) {
    store.delete(key);
    return undefined;
  }
  return entry;
}

export class RedisMockClient {
  constructor(private readonly store: UpstashMemoryStore = sharedUpstashStore) {}

  get<T = unknown>(key: string): Promise<T | null> {
    const entry = touch(this.store, key, Date.now());
    return Promise.resolve(entry ? (deserialize(entry.value) as T) : null);
  }

  set(
    key: string,
    value: unknown,
    opts?: { ex?: number; px?: number }
  ): Promise<string> {
    const now = Date.now();
    const expiresAt = opts?.px
      ? now + opts.px
      : opts?.ex
        ? now + opts.ex * 1000
        : undefined;
    this.store.set(key, { expiresAt, value: serialize(value) });
    return Promise.resolve("OK");
  }

  mset(pairs: Record<string, unknown> | Array<[string, unknown]>): Promise<string> {
    if (Array.isArray(pairs)) {
      for (const [k, v] of pairs) {
        this.store.set(k, { value: serialize(v) });
      }
    } else {
      for (const [k, v] of Object.entries(pairs)) {
        this.store.set(k, { value: serialize(v) });
      }
    }
    return Promise.resolve("OK");
  }

  del(...keys: string[]): Promise<number> {
    let deleted = 0;
    keys.forEach((k) => {
      if (this.store.delete(k)) deleted += 1;
    });
    return Promise.resolve(deleted);
  }

  expire(key: string, ttlSeconds: number): Promise<number> {
    const entry = touch(this.store, key, Date.now());
    if (!entry || ttlSeconds <= 0) return Promise.resolve(0);
    entry.expiresAt = Date.now() + ttlSeconds * 1000;
    this.store.set(key, entry);
    return Promise.resolve(1);
  }

  ttl(key: string): Promise<number> {
    const now = Date.now();
    const entry = touch(this.store, key, now);
    if (!entry) return Promise.resolve(-2);
    if (!entry.expiresAt) return Promise.resolve(-1);
    return Promise.resolve(Math.max(0, Math.floor((entry.expiresAt - now) / 1000)));
  }

  incr(key: string): Promise<number> {
    const now = Date.now();
    const entry = touch(this.store, key, now);
    const current = entry ? Number(entry.value) || 0 : 0;
    const next = current + 1;
    this.store.set(key, { ...entry, value: String(next) });
    return Promise.resolve(next);
  }

  mget<T extends unknown[]>(...keys: string[]): Promise<T> {
    const now = Date.now();
    const results = keys.map((key) => {
      const entry = touch(this.store, key, now);
      return entry ? deserialize(entry.value) : null;
    });
    return Promise.resolve(results as T);
  }

  exists(...keys: string[]): Promise<number> {
    const now = Date.now();
    let count = 0;
    for (const key of keys) {
      const entry = touch(this.store, key, now);
      if (entry) count += 1;
    }
    return Promise.resolve(count);
  }

  // List operations ---------------------------------------------------------

  private getList(key: string, now: number): string[] {
    const entry = touch(this.store, key, now);
    if (!entry) return [];
    try {
      const parsed = JSON.parse(entry.value);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }

  private setList(key: string, list: string[], expiresAt?: number): void {
    this.store.set(key, { expiresAt, value: JSON.stringify(list) });
  }

  lpush(key: string, ...values: string[]): Promise<number> {
    const now = Date.now();
    const list = this.getList(key, now);
    list.unshift(...values);
    const entry = this.store.get(key);
    this.setList(key, list, entry?.expiresAt);
    return Promise.resolve(list.length);
  }

  rpush(key: string, ...values: string[]): Promise<number> {
    const now = Date.now();
    const list = this.getList(key, now);
    list.push(...values);
    const entry = this.store.get(key);
    this.setList(key, list, entry?.expiresAt);
    return Promise.resolve(list.length);
  }

  lrange(key: string, start: number, stop: number): Promise<string[]> {
    const now = Date.now();
    const list = this.getList(key, now);
    const normalizedStop = stop < 0 ? list.length + stop : stop;
    return Promise.resolve(list.slice(start, normalizedStop + 1));
  }

  ltrim(key: string, start: number, stop: number): Promise<"OK"> {
    const now = Date.now();
    const list = this.getList(key, now);
    const normalizedStop = stop < 0 ? list.length + stop : stop;
    const trimmed = list.slice(start, normalizedStop + 1);
    const entry = this.store.get(key);
    this.setList(key, trimmed, entry?.expiresAt);
    return Promise.resolve("OK");
  }

  lrem(key: string, count: number, value: string): Promise<number> {
    const now = Date.now();
    const list = this.getList(key, now);
    let removed = 0;
    const remaining = [];
    for (const item of list) {
      if (removed < Math.abs(count) && item === value) {
        removed += 1;
        if (count > 0) continue;
      }
      remaining.push(item);
    }
    const entry = this.store.get(key);
    this.setList(key, remaining, entry?.expiresAt);
    return Promise.resolve(removed);
  }

  llen(key: string): Promise<number> {
    const now = Date.now();
    return Promise.resolve(this.getList(key, now).length);
  }

  scan(
    cursor: number,
    opts?: { match?: string; count?: number }
  ): Promise<[number, string[]]> {
    const now = Date.now();
    const keys = [...this.store.keys()].filter((key) => {
      const entry = touch(this.store, key, now);
      if (!entry) return false;
      if (!opts?.match) return true;
      if (opts.match.endsWith("*")) {
        const prefix = opts.match.slice(0, -1);
        return key.startsWith(prefix);
      }
      return key === opts.match;
    });
    const count = opts?.count ?? keys.length;
    const slice = keys.slice(cursor, cursor + count);
    const nextCursor = cursor + slice.length >= keys.length ? 0 : cursor + slice.length;
    return Promise.resolve([nextCursor, slice]);
  }

  // Lua eval support for simple atomic operations
  async eval(
    script: string,
    keys: string[],
    args: Array<string | number>
  ): Promise<unknown> {
    // Support circuit-breaker script: INCR + EXPIRE
    if (script.includes("INCR") && script.includes("EXPIRE") && keys.length === 1) {
      const ttl = Number(args[0] ?? 0);
      const value = await this.incr(keys[0]);
      if (ttl > 0) {
        await this.expire(keys[0], ttl);
      }
      return value;
    }

    // Support DLQ script: LRANGE + LREM by entry id
    if (script.includes("LRANGE") && script.includes("LREM") && keys.length === 1) {
      const targetId = String(args[0] ?? "");
      const entries = await this.lrange(keys[0], 0, -1);
      for (const entry of entries) {
        try {
          const parsed = JSON.parse(entry);
          if (parsed?.id === targetId) {
            return await this.lrem(keys[0], 1, entry);
          }
        } catch {
          // ignore parse errors
        }
      }
      return 0;
    }

    return null;
  }
}

export class RedisMock {
  static fromEnv(): RedisMockClient {
    return new RedisMockClient(sharedUpstashStore);
  }

  constructor(options?: { store?: UpstashMemoryStore }) {
    const client = new RedisMockClient(options?.store ?? sharedUpstashStore);
    Object.assign(this, client);
  }
}

// biome-ignore lint/style/useNamingConvention: mirrors @upstash/redis export shape
export type RedisMockModule = { Redis: typeof RedisMock } & {
  __reset: () => void;
  store: UpstashMemoryStore;
};

export function createRedisMock(
  store: UpstashMemoryStore = sharedUpstashStore
): RedisMockModule {
  const reset = () => store.clear();
  return {
    __reset: reset,
    // biome-ignore lint/style/useNamingConvention: mirrors @upstash/redis export shape
    Redis: RedisMock,
    store,
  };
}

export function resetRedisStore(store: UpstashMemoryStore = sharedUpstashStore): void {
  store.clear();
}

export async function runUpstashCommand(
  store: UpstashMemoryStore,
  command: string[]
): Promise<unknown> {
  const [opRaw, ...args] = command;
  const op = opRaw?.toUpperCase();
  const client = new RedisMockClient(store);
  switch (op) {
    case "GET":
      if (!args[0]) return null;
      return await client.get(args[0]);
    case "SET":
      if (!args[0]) return null;
      return await client.set(args[0], args[1]);
    case "DEL":
      return client.del(...(args as string[]));
    case "EXPIRE":
      if (!args[0]) return null;
      return await client.expire(args[0], Number(args[1]));
    case "TTL":
      if (!args[0]) return null;
      return await client.ttl(args[0]);
    case "INCR":
      if (!args[0]) return null;
      return await client.incr(args[0]);
    case "MSET":
      return client.mset(objectFromTuples(args as string[]));
    default:
      return null;
  }
}

export async function runUpstashPipeline(
  store: UpstashMemoryStore,
  commands: unknown
): Promise<unknown[]> {
  if (!Array.isArray(commands)) return [];
  const results: unknown[] = [];
  for (const cmd of commands) {
    if (Array.isArray(cmd)) {
      // eslint-disable-next-line no-await-in-loop
      results.push(await runUpstashCommand(store, cmd.map(String)));
    }
  }
  return results;
}

function objectFromTuples(args: string[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i];
    const val = args[i + 1];
    if (key !== undefined && val !== undefined) result[key] = val;
  }
  return result;
}

// Re-export ratelimit mock for convenience
export {
  createRatelimitMock,
  type RatelimitMockModule,
} from "./ratelimit-mock";

// Lazy import to avoid require() which doesn't work in vitest ESM context
import { createRatelimitMock as createRl } from "./ratelimit-mock";

export type UpstashMocks = {
  redis: RedisMockModule;
  ratelimit: import("./ratelimit-mock").RatelimitMockModule;
};

/**
 * Creates Upstash mock instances (Redis + Ratelimit).
 * Use with vi.mock() at module scope, NOT inside beforeEach.
 *
 * @example
 * ```ts
 * import { vi } from "vitest";
 * import { setupUpstashMocks } from "@/test/upstash/redis-mock";
 *
 * const { redis, ratelimit } = setupUpstashMocks();
 * vi.mock("@upstash/redis", () => redis);
 * vi.mock("@upstash/ratelimit", () => ratelimit);
 *
 * beforeEach(() => {
 *   redis.__reset();
 *   ratelimit.__reset();
 * });
 * ```
 */
export function setupUpstashMocks(): UpstashMocks {
  const redis = createRedisMock();
  const ratelimit = createRl();
  return { ratelimit, redis };
}
