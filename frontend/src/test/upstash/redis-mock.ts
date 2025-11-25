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
