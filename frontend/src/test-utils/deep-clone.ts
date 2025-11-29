/**
 * Deeply clone values for tests, handling cycles via WeakMap.
 * Preserves functions and handles common built-ins (Date, Map, Set).
 */
export function deepCloneValue<T>(value: T, seen = new WeakMap()): T {
	if (value === null || typeof value !== "object") {
		return value;
	}

	if (seen.has(value)) {
		return seen.get(value) as T;
	}

	if (value instanceof Date) {
		return new Date(value.getTime()) as unknown as T;
	}

	if (value instanceof Map) {
		const clonedMap = new Map();
		seen.set(value, clonedMap);
		value.forEach((mapValue, key) => {
			clonedMap.set(key, deepCloneValue(mapValue, seen));
		});
		return clonedMap as unknown as T;
	}

	if (value instanceof Set) {
		const clonedSet = new Set();
		seen.set(value, clonedSet);
		value.forEach((setValue) => {
			clonedSet.add(deepCloneValue(setValue, seen));
		});
		return clonedSet as unknown as T;
	}

	if (Array.isArray(value)) {
		const clonedArray: unknown[] = [];
		seen.set(value, clonedArray);
		value.forEach((item, index) => {
			clonedArray[index] = deepCloneValue(item, seen);
		});
		return clonedArray as unknown as T;
	}

	const clonedObject: Record<string, unknown> = {};
	seen.set(value, clonedObject);
	Object.entries(value as Record<string, unknown>).forEach(([key, val]) => {
		clonedObject[key] = deepCloneValue(val, seen);
	});
	return clonedObject as T;
}
