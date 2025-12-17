/**
 * @fileoverview Zustand middleware that recomputes derived state on every update.
 */

import type { StateCreator, StoreMutatorIdentifier } from "zustand";

/**
 * Configuration for computed state middleware.
 *
 * @template T - The store state type.
 */
export interface ComputedConfig<T> {
  /**
   * Function that computes derived values from current state.
   * Should return only the computed properties, not the full state.
   */
  compute: (state: T) => Partial<T>;
}

/**
 * Zustand middleware that automatically updates computed properties on state changes.
 *
 * @template T - Store state type (must include both base and computed properties)
 * @template Mps - Mutator parameters (for middleware composition)
 * @template Mcs - Mutator constraints
 *
 * @param config - Configuration object with compute function
 * @param stateCreator - Zustand state creator to wrap
 * @returns Middleware-wrapped state creator
 *
 * @example
 * ```ts
 * const useStore = create<State>()(
 *   withComputed(
 *     { compute: (state) => ({ total: state.price * state.qty }) },
 *     (set) => ({
 *       price: 0,
 *       qty: 1,
 *       total: 0,
 *       setPrice: (price) => set({ price }),
 *     })
 *   )
 * );
 * ```
 *
 * @remarks
 * Compute functions run on **every state update**. Keep them pure, synchronous,
 * and efficient (O(1) or O(n) with small n). See the Zustand Computed Middleware
 * Guide for patterns, performance tips, and when to use vs. selectors.
 */
export function withComputed<
  T extends object,
  Mps extends [StoreMutatorIdentifier, unknown][] = [],
  Mcs extends [StoreMutatorIdentifier, unknown][] = [],
>(
  config: ComputedConfig<T>,
  stateCreator: StateCreator<T, Mps, Mcs>
): StateCreator<T, Mps, Mcs> {
  return (set, get, api) => {
    const applyComputed = (
      nextState: Parameters<typeof set>[0],
      replace?: Parameters<typeof set>[1]
    ) => {
      const partialState =
        typeof nextState === "function" ? nextState(get()) : nextState;
      const mergedState =
        replace === true ? partialState : { ...get(), ...partialState };
      const derived = config.compute(mergedState as T);
      return { derived, partialState, replace: replace === true };
    };

    const computedSet = ((...args: Parameters<typeof set>) => {
      const [nextState, replace] = args;
      const { derived, partialState } = applyComputed(nextState, replace);
      const updatedArgs = [...args] as Parameters<typeof set>;

      updatedArgs[0] = (
        replace === true
          ? ({ ...(partialState as T), ...derived } as T)
          : (state: T) => ({ ...state, ...partialState, ...derived })
      ) as Parameters<typeof set>[0];

      const setFn = set as (
        ...setArgs: Parameters<typeof set>
      ) => ReturnType<typeof set>;
      return setFn(...updatedArgs);
    }) as typeof set;

    const originalSetState = api.setState;
    api.setState = ((...args: Parameters<typeof api.setState>) => {
      const [nextState, replace] = args;
      const { derived, partialState } = applyComputed(
        nextState as Parameters<typeof set>[0],
        replace as Parameters<typeof set>[1]
      );
      const updatedArgs = [...args] as Parameters<typeof api.setState>;

      updatedArgs[0] = (
        replace === true
          ? ({ ...(partialState as T), ...derived } as T)
          : (state: T) => ({ ...state, ...partialState, ...derived })
      ) as Parameters<typeof api.setState>[0];

      const setStateFn = originalSetState as (
        ...setArgs: Parameters<typeof api.setState>
      ) => ReturnType<typeof api.setState>;
      return setStateFn(...updatedArgs);
    }) as typeof api.setState;

    return stateCreator(computedSet, get, api);
  };
}

/**
 * Helper to create a compute function from individual computed properties.
 *
 * @template T - The store state type.
 * @param computedProps - Object mapping property names to compute functions.
 * @returns Combined compute function.
 */
export function createComputeFn<T>(
  computedProps: { [K in keyof Partial<T>]: (state: T) => T[K] }
): (state: T) => Partial<T> {
  return (state: T) => {
    const result: Partial<T> = {};
    for (const [key, fn] of Object.entries(computedProps)) {
      result[key as keyof T] = (fn as (s: T) => T[keyof T])(state);
    }
    return result;
  };
}
