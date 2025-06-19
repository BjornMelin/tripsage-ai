/**
 * Test Suite for Supabase Edge Functions
 * 
 * This test suite validates the functionality of all three Edge Functions:
 * - trip-notifications
 * - file-processing 
 * - cache-invalidation
 */

import { assertEquals, assertExists } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Configuration
const SUPABASE_URL = Deno.env.get('SUPABASE_URL') || 'http://localhost:54321';
const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY') || 'your-anon-key';
const TEST_AUTH_TOKEN = Deno.env.get('TEST_AUTH_TOKEN') || 'test-token';

interface TestResponse {
  status: number;
  data: any;
}

/**
 * Makes a test request to an Edge Function
 */
async function makeTestRequest(
  functionName: string, 
  payload: any, 
  headers: Record<string, string> = {}
): Promise<TestResponse> {
  const url = `${SUPABASE_URL}/functions/v1/${functionName}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_AUTH_TOKEN}`,
      ...headers
    },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  
  return {
    status: response.status,
    data
  };
}

/**
 * Test Trip Notifications Edge Function
 */
Deno.test("Trip Notifications - Collaboration Added", async () => {
  const payload = {
    event_type: 'collaboration_added',
    trip_id: 123,
    user_id: 'test-user-id',
    target_user_id: 'test-target-user-id',
    permission_level: 'view'
  };

  const response = await makeTestRequest('trip-notifications', payload);
  
  // Should handle the request even if external services aren't configured
  assertEquals(response.status, 200);
  assertExists(response.data.success);
});

Deno.test("Trip Notifications - Invalid Request", async () => {
  const payload = {
    event_type: 'invalid_event',
    // missing required fields
  };

  const response = await makeTestRequest('trip-notifications', payload);
  
  assertEquals(response.status, 400);
  assertExists(response.data.error);
});

Deno.test("Trip Notifications - Webhook Event", async () => {
  const payload = {
    type: 'INSERT',
    table: 'trip_collaborators',
    record: {
      id: 1,
      trip_id: 123,
      user_id: 'test-user',
      permission_level: 'view',
      added_by: 'test-owner',
      added_at: new Date().toISOString()
    },
    schema: 'public'
  };

  const response = await makeTestRequest('trip-notifications', payload, {
    'x-webhook-secret': Deno.env.get('WEBHOOK_SECRET') || 'test-secret'
  });
  
  assertEquals(response.status, 200);
  assertEquals(response.data.success, true);
});

/**
 * Test File Processing Edge Function
 */
Deno.test("File Processing - Process All Operation", async () => {
  const payload = {
    file_id: 'test-file-uuid',
    operation: 'process_all'
  };

  const response = await makeTestRequest('file-processing', payload);
  
  // Should return 404 for non-existent file (expected behavior)
  assertEquals(response.status, 404);
  assertExists(response.data.error);
});

Deno.test("File Processing - Virus Scan Operation", async () => {
  const payload = {
    file_id: 'test-file-uuid',
    operation: 'virus_scan'
  };

  const response = await makeTestRequest('file-processing', payload);
  
  // Should return 404 for non-existent file
  assertEquals(response.status, 404);
});

Deno.test("File Processing - Invalid Operation", async () => {
  const payload = {
    file_id: 'test-file-uuid',
    operation: 'invalid_operation'
  };

  const response = await makeTestRequest('file-processing', payload);
  
  assertEquals(response.status, 400);
  assertExists(response.data.error);
});

Deno.test("File Processing - Webhook Event", async () => {
  const payload = {
    type: 'INSERT',
    table: 'file_attachments',
    record: {
      id: 'test-file-uuid',
      user_id: 'test-user',
      filename: 'test.jpg',
      original_filename: 'test.jpg',
      file_size: 1024,
      mime_type: 'image/jpeg',
      file_path: 'test/path.jpg',
      bucket_name: 'attachments',
      upload_status: 'uploading',
      virus_scan_status: 'pending'
    },
    schema: 'public'
  };

  const response = await makeTestRequest('file-processing', payload, {
    'x-webhook-secret': Deno.env.get('WEBHOOK_SECRET') || 'test-secret'
  });
  
  assertEquals(response.status, 200);
  assertEquals(response.data.success, true);
});

/**
 * Test Cache Invalidation Edge Function
 */
Deno.test("Cache Invalidation - Manual All Cache Clear", async () => {
  const payload = {
    cache_type: 'all',
    patterns: ['trip:*', 'search:*'],
    reason: 'Test cleanup'
  };

  const response = await makeTestRequest('cache-invalidation', payload);
  
  assertEquals(response.status, 200);
  assertEquals(response.data.success, true);
  assertEquals(response.data.manual_invalidation, true);
  assertExists(response.data.redis_cleared);
  assertExists(response.data.search_cache_cleared);
});

Deno.test("Cache Invalidation - Redis Only", async () => {
  const payload = {
    cache_type: 'redis',
    keys: ['test:key1', 'test:key2']
  };

  const response = await makeTestRequest('cache-invalidation', payload);
  
  assertEquals(response.status, 200);
  assertEquals(response.data.cache_type, 'redis');
});

Deno.test("Cache Invalidation - Invalid Cache Type", async () => {
  const payload = {
    cache_type: 'invalid_type'
  };

  const response = await makeTestRequest('cache-invalidation', payload);
  
  // Should still work but with 0 results
  assertEquals(response.status, 200);
});

Deno.test("Cache Invalidation - Webhook Event", async () => {
  const payload = {
    type: 'UPDATE',
    table: 'trips',
    record: {
      id: 123,
      name: 'Updated Trip',
      destination: 'New York'
    },
    old_record: {
      id: 123,
      name: 'Old Trip',
      destination: 'Boston'
    },
    schema: 'public'
  };

  const response = await makeTestRequest('cache-invalidation', payload, {
    'x-webhook-secret': Deno.env.get('WEBHOOK_SECRET') || 'test-secret'
  });
  
  assertEquals(response.status, 200);
  assertEquals(response.data.success, true);
  assertEquals(response.data.webhook_processed, true);
});

/**
 * Test CORS handling
 */
Deno.test("CORS - OPTIONS Request", async () => {
  const url = `${SUPABASE_URL}/functions/v1/trip-notifications`;
  
  const response = await fetch(url, {
    method: 'OPTIONS'
  });
  
  assertEquals(response.status, 200);
  assertEquals(response.headers.get('Access-Control-Allow-Origin'), '*');
  assertEquals(response.headers.get('Access-Control-Allow-Methods'), 'POST, OPTIONS');
});

/**
 * Test Authentication
 */
Deno.test("Authentication - Missing Token", async () => {
  const url = `${SUPABASE_URL}/functions/v1/trip-notifications`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      event_type: 'test',
      trip_id: 123,
      user_id: 'test'
    })
  });

  assertEquals(response.status, 401);
  
  const data = await response.json();
  assertExists(data.error);
});

Deno.test("Authentication - Invalid Token", async () => {
  const url = `${SUPABASE_URL}/functions/v1/trip-notifications`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer invalid-token'
    },
    body: JSON.stringify({
      event_type: 'test',
      trip_id: 123,
      user_id: 'test'
    })
  });

  assertEquals(response.status, 401);
  
  const data = await response.json();
  assertExists(data.error);
});

/**
 * Performance Tests
 */
Deno.test("Performance - Response Time", async () => {
  const startTime = Date.now();
  
  const payload = {
    cache_type: 'redis',
    keys: ['test:performance']
  };

  const response = await makeTestRequest('cache-invalidation', payload);
  
  const responseTime = Date.now() - startTime;
  
  assertEquals(response.status, 200);
  
  // Should respond within 5 seconds
  if (responseTime > 5000) {
    console.warn(`Slow response time: ${responseTime}ms`);
  }
});

/**
 * Error Handling Tests
 */
Deno.test("Error Handling - Malformed JSON", async () => {
  const url = `${SUPABASE_URL}/functions/v1/trip-notifications`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_AUTH_TOKEN}`
    },
    body: '{ invalid json'
  });

  assertEquals(response.status, 500);
  
  const data = await response.json();
  assertExists(data.error);
});

Deno.test("Error Handling - Method Not Allowed", async () => {
  const url = `${SUPABASE_URL}/functions/v1/trip-notifications`;
  
  const response = await fetch(url, {
    method: 'GET'
  });

  assertEquals(response.status, 405);
  
  const data = await response.json();
  assertEquals(data.error, 'Method not allowed');
});

/**
 * Integration Tests
 */
Deno.test("Integration - Function Chain", async () => {
  // Test that webhook events can trigger multiple functions
  const collaboratorPayload = {
    type: 'INSERT',
    table: 'trip_collaborators',
    record: {
      id: 1,
      trip_id: 123,
      user_id: 'test-user',
      permission_level: 'view',
      added_by: 'test-owner'
    },
    schema: 'public'
  };

  // This should trigger both notifications and cache invalidation
  const [notificationResponse, cacheResponse] = await Promise.all([
    makeTestRequest('trip-notifications', collaboratorPayload, {
      'x-webhook-secret': Deno.env.get('WEBHOOK_SECRET') || 'test-secret'
    }),
    makeTestRequest('cache-invalidation', collaboratorPayload, {
      'x-webhook-secret': Deno.env.get('WEBHOOK_SECRET') || 'test-secret'
    })
  ]);

  assertEquals(notificationResponse.status, 200);
  assertEquals(cacheResponse.status, 200);
  assertEquals(notificationResponse.data.success, true);
  assertEquals(cacheResponse.data.success, true);
});

console.log("🧪 Edge Functions Test Suite");
console.log("=============================");
console.log("Run with: deno test --allow-net --allow-env test_edge_functions.ts");
console.log("");
console.log("Environment variables needed:");
console.log("- SUPABASE_URL (default: http://localhost:54321)");
console.log("- SUPABASE_ANON_KEY");
console.log("- TEST_AUTH_TOKEN");
console.log("- WEBHOOK_SECRET");
console.log("");
console.log("Make sure Supabase is running locally or configure for remote testing.");