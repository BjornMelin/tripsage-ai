/**
 * Cache Invalidation Edge Function
 * 
 * Handles cache invalidation operations including:
 * - Database change event processing
 * - Upstash Redis cache clearing
 * - Search cache table updates
 * - Application layer notifications
 * 
 * @module cache-invalidation
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.1";
import { Redis } from "https://deno.land/x/upstash_redis@v1.22.0/mod.ts";

// Type definitions
interface WebhookPayload {
  type: 'INSERT' | 'UPDATE' | 'DELETE';
  table: string;
  record: Record<string, any>;
  old_record?: Record<string, any>;
  schema: string;
}

interface CacheInvalidationRequest {
  cache_type: 'redis' | 'search_cache' | 'all';
  keys?: string[];
  patterns?: string[];
  tables?: string[];
  reason?: string;
}

interface CacheInvalidationResult {
  success: boolean;
  redis_cleared: number;
  search_cache_cleared: number;
  notifications_sent: number;
  errors: string[];
}

// Environment variables
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const UPSTASH_REDIS_REST_URL = Deno.env.get('UPSTASH_REDIS_REST_URL')!;
const UPSTASH_REDIS_REST_TOKEN = Deno.env.get('UPSTASH_REDIS_REST_TOKEN')!;
const CACHE_WEBHOOK_URL = Deno.env.get('CACHE_WEBHOOK_URL');

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Cache patterns for different data types
const CACHE_PATTERNS = {
  trips: ['trip:*', 'user_trips:*', 'trip_search:*'],
  flights: ['flight:*', 'flight_search:*', 'search_flights:*'],
  accommodations: ['accommodation:*', 'hotel_search:*', 'search_hotels:*'],
  destinations: ['destination:*', 'destination_search:*', 'search_destinations:*'],
  activities: ['activity:*', 'activity_search:*', 'search_activities:*'],
  users: ['user:*', 'user_profile:*', 'user_preferences:*'],
  search: ['search:*', 'search_cache:*', 'search_results:*'],
  memory: ['memory:*', 'chat_memory:*', 'conversation:*']
};

/**
 * Validates the incoming request and authentication
 */
async function validateRequest(req: Request): Promise<{ isValid: boolean; error?: string }> {
  try {
    // Check for webhook secret first
    const webhookSecret = req.headers.get('x-webhook-secret');
    if (webhookSecret === Deno.env.get('WEBHOOK_SECRET')) {
      return { isValid: true };
    }

    // Check for authorization header
    const authHeader = req.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return { isValid: false, error: 'Missing or invalid authorization header' };
    }

    // Verify JWT token
    const token = authHeader.replace('Bearer ', '');
    const { data: { user }, error } = await supabase.auth.getUser(token);
    
    if (error || !user) {
      return { isValid: false, error: 'Invalid authentication token' };
    }

    return { isValid: true };
  } catch (error) {
    console.error('Validation error:', error);
    return { isValid: false, error: 'Request validation failed' };
  }
}

/**
 * Connects to Upstash Redis
 */
function connectToRedis() {
  try {
    if (!UPSTASH_REDIS_REST_URL || !UPSTASH_REDIS_REST_TOKEN) return null;
    return new Redis({ url: UPSTASH_REDIS_REST_URL, token: UPSTASH_REDIS_REST_TOKEN });
  } catch (error) {
    console.error('Upstash init error:', error);
    return null;
  }
}

/**
 * Clears Redis cache keys by pattern
 */
async function clearRedisCache(patterns: string[]): Promise<number> {
  const redis = connectToRedis();
  if (!redis) {
    console.error('Failed to initialize Upstash Redis');
    return 0;
  }

  let totalCleared = 0;

  try {
    for (const pattern of patterns) {
      console.log(`Clearing Redis keys matching pattern: ${pattern}`);
      
      // Get all keys matching the pattern
      const keys = await redis.keys(pattern);
      
      if (keys.length > 0) {
        // Delete keys in batches to avoid blocking
        const batchSize = 100;
        for (let i = 0; i < keys.length; i += batchSize) {
          const batch = keys.slice(i, i + batchSize);
          // Upstash del supports variadic keys as array via spread
          await redis.del(...batch);
          totalCleared += batch.length;
        }
        console.log(`Cleared ${keys.length} keys for pattern ${pattern}`);
      }
    }
  } catch (error) {
    console.error('Redis clear error:', error);
  } finally {
    // Upstash is HTTP-based; no explicit quit required
  }

  return totalCleared;
}

/**
 * Clears specific Redis cache keys
 */
async function clearRedisKeys(keys: string[]): Promise<number> {
  const redis = connectToRedis();
  if (!redis) {
    console.error('Failed to initialize Upstash Redis');
    return 0;
  }

  let totalCleared = 0;

  try {
    if (keys.length > 0) {
      // Delete keys in batches
      const batchSize = 100;
      for (let i = 0; i < keys.length; i += batchSize) {
        const batch = keys.slice(i, i + batchSize);
        const result = await redis.del(...batch);
        totalCleared += result;
      }
      console.log(`Cleared ${totalCleared} specific Redis keys`);
    }
  } catch (error) {
    console.error('Redis key clear error:', error);
  } finally {
    await redis.quit();
  }

  return totalCleared;
}

/**
 * Clears search cache tables in database
 */
async function clearSearchCache(tables: string[]): Promise<number> {
  let totalCleared = 0;

  try {
    const searchTables = ['search_destinations', 'search_flights', 'search_hotels', 'search_activities'];
    const tablesToClear = tables.length > 0 ? 
      searchTables.filter(table => tables.includes(table)) : 
      searchTables;

    for (const table of tablesToClear) {
      console.log(`Clearing search cache table: ${table}`);
      
      // Delete expired entries (older than 24 hours)
      const { count, error } = await supabase
        .from(table)
        .delete()
        .lt('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString());

      if (error) {
        console.error(`Error clearing ${table}:`, error);
      } else {
        console.log(`Cleared ${count || 0} entries from ${table}`);
        totalCleared += count || 0;
      }
    }
  } catch (error) {
    console.error('Search cache clear error:', error);
  }

  return totalCleared;
}

/**
 * Sends webhook notification about cache invalidation
 */
async function notifyApplications(invalidationData: any): Promise<boolean> {
  if (!CACHE_WEBHOOK_URL) {
    console.log('No cache webhook URL configured, skipping notification');
    return true;
  }

  try {
    const response = await fetch(CACHE_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Event-Type': 'cache-invalidation'
      },
      body: JSON.stringify({
        timestamp: new Date().toISOString(),
        event_type: 'cache_invalidated',
        ...invalidationData
      })
    });

    if (!response.ok) {
      console.error('Cache webhook notification failed:', response.status);
      return false;
    }

    return true;
  } catch (error) {
    console.error('Cache webhook error:', error);
    return false;
  }
}

/**
 * Determines cache patterns to clear based on table changes
 */
function getCachePatternsForTable(tableName: string): string[] {
  const patterns: string[] = [];

  switch (tableName) {
    case 'trips':
      patterns.push(...CACHE_PATTERNS.trips);
      patterns.push(...CACHE_PATTERNS.search); // Trip searches affect search cache
      break;
    case 'flights':
      patterns.push(...CACHE_PATTERNS.flights);
      patterns.push(...CACHE_PATTERNS.search);
      break;
    case 'accommodations':
      patterns.push(...CACHE_PATTERNS.accommodations);
      patterns.push(...CACHE_PATTERNS.search);
      break;
    case 'search_destinations':
    case 'search_flights':
    case 'search_hotels':
    case 'search_activities':
      patterns.push(...CACHE_PATTERNS.search);
      break;
    case 'trip_collaborators':
      patterns.push(...CACHE_PATTERNS.trips);
      patterns.push(...CACHE_PATTERNS.users);
      break;
    case 'chat_messages':
    case 'chat_sessions':
      patterns.push(...CACHE_PATTERNS.memory);
      break;
    case 'users':
      patterns.push(...CACHE_PATTERNS.users);
      break;
    default:
      // For unknown tables, clear general caches
      patterns.push('search:*', 'cache:*');
  }

  return patterns;
}

/**
 * Handles database webhook events for automatic cache invalidation
 */
async function handleWebhookEvent(payload: WebhookPayload): Promise<CacheInvalidationResult> {
  console.log('Processing cache invalidation for:', payload.type, payload.table);

  const result: CacheInvalidationResult = {
    success: true,
    redis_cleared: 0,
    search_cache_cleared: 0,
    notifications_sent: 0,
    errors: []
  };

  try {
    // Determine cache patterns to clear
    const patterns = getCachePatternsForTable(payload.table);

    // Clear Redis cache
    if (patterns.length > 0) {
      result.redis_cleared = await clearRedisCache(patterns);
    }

    // Clear search cache if relevant
    if (payload.table.startsWith('search_') || ['trips', 'flights', 'accommodations'].includes(payload.table)) {
      result.search_cache_cleared = await clearSearchCache([]);
    }

    // Notify applications
    const notificationSent = await notifyApplications({
      table: payload.table,
      operation: payload.type,
      patterns_cleared: patterns,
      record_id: payload.record?.id || 'unknown'
    });

    if (notificationSent) {
      result.notifications_sent = 1;
    }

    // Log specific invalidations for important changes
    if (payload.table === 'trips' && payload.record?.id) {
      console.log(`Invalidated caches for trip ${payload.record.id}`);
    }

  } catch (error) {
    console.error('Cache invalidation error:', error);
    result.success = false;
    result.errors.push(error instanceof Error ? error.message : 'Unknown error');
  }

  return result;
}

/**
 * Performs manual cache invalidation
 */
async function performManualInvalidation(request: CacheInvalidationRequest): Promise<CacheInvalidationResult> {
  const result: CacheInvalidationResult = {
    success: true,
    redis_cleared: 0,
    search_cache_cleared: 0,
    notifications_sent: 0,
    errors: []
  };

  try {
    if (request.cache_type === 'redis' || request.cache_type === 'all') {
      // Clear specific keys if provided
      if (request.keys && request.keys.length > 0) {
        result.redis_cleared += await clearRedisKeys(request.keys);
      }

      // Clear patterns if provided
      if (request.patterns && request.patterns.length > 0) {
        result.redis_cleared += await clearRedisCache(request.patterns);
      }
    }

    if (request.cache_type === 'search_cache' || request.cache_type === 'all') {
      result.search_cache_cleared = await clearSearchCache(request.tables || []);
    }

    // Notify applications
    const notificationSent = await notifyApplications({
      manual_invalidation: true,
      cache_type: request.cache_type,
      reason: request.reason || 'Manual invalidation',
      keys: request.keys,
      patterns: request.patterns,
      tables: request.tables
    });

    if (notificationSent) {
      result.notifications_sent = 1;
    }

  } catch (error) {
    console.error('Manual invalidation error:', error);
    result.success = false;
    result.errors.push(error instanceof Error ? error.message : 'Unknown error');
  }

  return result;
}

/**
 * Main request handler
 */
serve(async (req: Request) => {
  try {
    // Handle CORS preflight
    if (req.method === 'OPTIONS') {
      return new Response('ok', {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'authorization, content-type, x-webhook-secret',
        },
      });
    }

    // Only accept POST requests
    if (req.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check if this is a webhook request
    const webhookSecret = req.headers.get('x-webhook-secret');
    if (webhookSecret === Deno.env.get('WEBHOOK_SECRET')) {
      // Process webhook event
      const payload = await req.json() as WebhookPayload;
      const result = await handleWebhookEvent(payload);
      
      return new Response(JSON.stringify({ 
        success: true,
        webhook_processed: true,
        ...result
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate regular API request
    const validation = await validateRequest(req);
    if (!validation.isValid) {
      return new Response(JSON.stringify({ error: validation.error }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Process manual cache invalidation request
    const invalidationReq = await req.json() as CacheInvalidationRequest;

    // Validate required fields
    if (!invalidationReq.cache_type) {
      return new Response(JSON.stringify({ error: 'cache_type is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Perform invalidation
    const result = await performManualInvalidation(invalidationReq);

    return new Response(JSON.stringify({ 
      success: result.success,
      manual_invalidation: true,
      cache_type: invalidationReq.cache_type,
      ...result
    }), {
      status: result.success ? 200 : 500,
      headers: { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });

  } catch (error) {
    console.error('Function error:', error);
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
});
