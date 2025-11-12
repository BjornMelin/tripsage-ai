/**
 * @fileoverview Shared constants for planning tools.
 */

export const RATE_CREATE_PER_DAY = 20; // per user
export const RATE_UPDATE_PER_MIN = 60; // per plan

export const TTL_DRAFT_SECONDS = 86400 * 7; // 7 days
export const TTL_FINAL_SECONDS = 86400 * 30; // 30 days

/**
 * Cache TTL for accommodation search results (5 minutes).
 * Used by searchAccommodations tool.
 */
export const ACCOM_SEARCH_CACHE_TTL_SECONDS = 300;

/**
 * Cache TTL for weather results (10 minutes).
 * Used by getCurrentWeather tool.
 */
export const WEATHER_CACHE_TTL_SECONDS = 600;
