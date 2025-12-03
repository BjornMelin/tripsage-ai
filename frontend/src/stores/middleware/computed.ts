/**
 * @fileoverview Zustand middleware for automatic computed state derivation.
 *
 * Provides a reusable middleware that recalculates derived values after each
 * state update, keeping computed properties in sync.
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
 * Zustand middleware that automatically updates computed properties
 * after each state change.
 *
 * @template T - The store state type.
 * @template Mps - Mutator parameters (for middleware composition).
 * @template Mcs - Mutator constraints.
 *
 * @param config - Configuration with compute function.
 * @param stateCreator - Original state creator.
 * @returns Middleware-wrapped state creator for `create()`.
 *
 * @example
 * const useStore = create<MyState>()(
 *   withComputed(
 *     { compute: (state) => ({ total: state.items.length }) },
 *     (set, get) => ({
 *       items: [],
 *       total: 0,
 *       addItem: (item) => set({ items: [...get().items, item] }),
 *     })
 *   )
 * );
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
      const mergedState = replace ? partialState : { ...get(), ...partialState };
      const derived = config.compute(mergedState as T);
      return { derived, partialState, replace: replace === true };
    };

    const computedSet = ((...args: Parameters<typeof set>) => {
      const [nextState, replace] = args;
      const { derived, partialState } = applyComputed(nextState, replace);
      const updatedArgs = [...args] as Parameters<typeof set>;
      updatedArgs[0] = (
        replace
          ? ({ ...(partialState as T), ...derived } as T)
          : (((state) => ({ ...state, ...partialState, ...derived })) as Parameters<
              typeof set
            >[0])
      ) as Parameters<typeof set>[0];
      return (
        set as unknown as (...setArgs: Parameters<typeof set>) => ReturnType<typeof set>
      )(...(updatedArgs as unknown as Parameters<typeof set>));
    }) as typeof set;

    const originalSetState = api.setState;
    api.setState = ((...args: Parameters<typeof api.setState>) => {
      const [nextState, replace] = args;
      const { derived, partialState } = applyComputed(nextState, replace);
      const updatedArgs = [...args] as Parameters<typeof api.setState>;
      updatedArgs[0] = (
        replace
          ? ({ ...(partialState as T), ...derived } as T)
          : (((state) => ({ ...state, ...partialState, ...derived })) as Parameters<
              typeof api.setState
            >[0])
      ) as Parameters<typeof api.setState>[0];
      return (
        originalSetState as unknown as (
          ...setArgs: Parameters<typeof api.setState>
        ) => ReturnType<typeof api.setState>
      )(...(updatedArgs as unknown as Parameters<typeof api.setState>));
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
