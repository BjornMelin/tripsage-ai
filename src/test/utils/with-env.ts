import { vi } from "vitest";

/**
 * Execute a test with isolated environment variables.
 * Saves current env, applies changes, resets modules, executes callback, then restores.
 */
export async function withEnv<T>(
  values: Record<string, string | undefined>,
  fn: () => T | Promise<T>
): Promise<T> {
  const prev = new Map<string, string | undefined>();
  for (const [key, value] of Object.entries(values)) {
    prev.set(key, process.env[key]);
    if (value === undefined) {
      Reflect.deleteProperty(process.env, key);
    } else {
      process.env[key] = value;
    }
  }

  vi.resetModules();
  try {
    return await fn();
  } finally {
    vi.resetModules();
    for (const [key, value] of prev.entries()) {
      if (value === undefined) {
        Reflect.deleteProperty(process.env, key);
      } else {
        process.env[key] = value;
      }
    }
  }
}
