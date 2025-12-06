/**
 * @fileoverview Registry for all search parameter handlers
 * Each handler is responsible for a specific search type's parameter validation, defaults, and serialization.
 * Handlers are automatically registered when imported.
 */

import { accommodationHandler } from "./accommodation-handler";
import { activityHandler } from "./activity-handler";
import { destinationHandler } from "./destination-handler";
import { flightHandler } from "./flight-handler";

export const registerAllHandlers = () => {
  // Handlers self-register on import via registerHandler.
  return [destinationHandler, accommodationHandler, activityHandler, flightHandler];
};

export { accommodationHandler, activityHandler, destinationHandler, flightHandler };
