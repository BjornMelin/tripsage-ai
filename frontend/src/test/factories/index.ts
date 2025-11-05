/**
 * @fileoverview Test data factories for creating consistent test data.
 * Provides builder-pattern factories for common domain objects with sensible defaults.
 *
 * Usage:
 *   import { createUser, createTrip, createFlight, resetAllFactories } from "@/test/factories";
 *
 *   beforeEach(() => {
 *     resetAllFactories(); // Reset ID counters for deterministic tests
 *   });
 *
 *   it("should create a user", () => {
 *     const user = createUser({ email: "test@example.com" });
 *     expect(user.id).toBe("user-1"); // Deterministic ID
 *   });
 *
 *   it("should create a trip", () => {
 *     const trip = createTrip({ destination: "Paris", budget: 3000 });
 *     expect(trip.budget).toBe(3000);
 *   });
 *
 *   it("should create multiple results", () => {
 *     const results = createSearchResults(5, (i) => ({ price: 100 + i * 50 }));
 *     expect(results).toHaveLength(5);
 *     expect(results[0].price).toBe(100);
 *     expect(results[4].price).toBe(300);
 *   });
 */

export * from "./filter-factory";
export * from "./reset";
export * from "./search-factory";
export * from "./trip-factory";
export * from "./user-factory";
