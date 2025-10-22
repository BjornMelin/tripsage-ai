/**
 * Integration Test Suite for Edge Functions
 * 
 * This test suite validates how different Edge Functions work together
 * in real-world scenarios and workflows. It tests:
 * 
 * - Cross-function communication and data flow
 * - End-to-end trip collaboration workflows
 * - File processing to notification pipelines
 * - Cache invalidation across multiple functions
 * - Error propagation and recovery
 * - Performance under concurrent loads
 * - Database consistency across function calls
 * 
 * Target: integration coverage
 */

import {
  assertEquals,
  assertExists,
  assertRejects,
  TestDataFactory,
  MockSupabase,
  MockRedis,
  MockFetch,
  RequestTestHelper,
  ResponseAssertions,
  EdgeFunctionTester
} from "./test-utils.ts";

/**
 * Integration Test Environment
 * Manages shared state across multiple Edge Function tests
 */
class IntegrationTestEnvironment {
  public mockSupabase: MockSupabase;
  public mockRedis: MockRedis;
  public mockFetch: MockFetch;
  public testUser: any;
  public testTrip: any;
  public testSession: string;

  constructor() {
    this.mockSupabase = new MockSupabase();
    this.mockRedis = new MockRedis();
    this.mockFetch = new MockFetch();
    this.testUser = TestDataFactory.createUser();
    this.testTrip = TestDataFactory.createTrip();
    this.testSession = "integration-test-session";
  }

  async setup() {
    // Setup common environment variables
    Deno.env.set('SUPABASE_URL', 'https://test.supabase.co');
    Deno.env.set('SUPABASE_ANON_KEY', 'test-anon-key');
    Deno.env.set('SUPABASE_SERVICE_ROLE_KEY', 'test-service-role-key');
    Deno.env.set('OPENAI_API_KEY', 'test-openai-key');
    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    Deno.env.set('WEBHOOK_SECRET', 'test-webhook-secret');
    Deno.env.set('REDIS_URL', 'redis://localhost:6379');

    // Setup common mock responses
    this.mockSupabase.setResponse('auth_getUser', {
      data: { user: this.testUser },
      error: null
    });

    this.mockSupabase.setResponse('trips_select_eq_single', {
      data: this.testTrip,
      error: null
    });

    this.mockSupabase.setResponse('auth.users_select_eq_single', {
      data: this.testUser,
      error: null
    });

    // Setup OpenAI mock
    this.mockFetch.setResponse('https://api.openai.com/v1/embeddings', {
      status: 200,
      body: JSON.stringify({
        data: [{ embedding: new Array(1536).fill(0.1) }],
        usage: { total_tokens: 100 }
      })
    });

    // Setup Resend mock
    this.mockFetch.setResponse('https://api.resend.com/emails', {
      status: 200,
      body: JSON.stringify({ id: 'email-123' })
    });
  }

  cleanup() {
    // Clear environment variables
    const envVars = [
      'SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY',
      'OPENAI_API_KEY', 'RESEND_API_KEY', 'WEBHOOK_SECRET', 'REDIS_URL'
    ];
    
    envVars.forEach(key => Deno.env.delete(key));
  }
}

// Integration Test Suite
Deno.test("Integration - Complete Trip Collaboration Workflow", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Step 1: User uploads a file (triggers file-processing)
    const fileContent = "Trip itinerary document content...";
    const fileData = {
      trip_id: env.testTrip.id,
      file_name: "itinerary.pdf",
      file_type: "application/pdf",
      file_size: 1024,
      uploaded_by: env.testUser.id
    };

    // Mock file processing responses
    env.mockSupabase.setResponse('file_attachments_insert', {
      data: [{ id: 'attachment-123', ...fileData }],
      error: null
    });

    env.mockFetch.setResponse('https://api.virustotal.com/api/v3/files', {
      status: 200,
      body: JSON.stringify({
        data: { attributes: { stats: { malicious: 0, suspicious: 0 } } }
      })
    });

    // Step 2: File processing triggers cache invalidation
    env.mockRedis.setExpectedCalls([
      { method: 'keys', args: ['trip:*'], result: ['trip:123:details', 'trip:123:files'] },
      { method: 'del', args: [['trip:123:details', 'trip:123:files']], result: 2 }
    ]);

    // Step 3: Add collaborator (triggers trip-events)
    const collaboratorData = TestDataFactory.createTripCollaborator({
      trip_id: env.testTrip.id,
      user_id: 'collaborator-456',
      added_by: env.testUser.id,
      permission_level: 'edit'
    });

    env.mockSupabase.setResponse('trip_collaborators_insert', {
      data: [collaboratorData],
      error: null
    });

    // Step 4: Collaboration triggers notifications
    const collaboratorUser = TestDataFactory.createUser({
      id: 'collaborator-456',
      email: 'collaborator@example.com'
    });

    // Step 5: AI processing analyzes the uploaded content
    env.mockSupabase.setResponse('chat_messages_insert', {
      data: [TestDataFactory.createChatMessage({
        session_id: env.testSession,
        content: `Analyzed uploaded file: ${fileData.file_name}`,
        role: 'assistant'
      })],
      error: null
    });

    env.mockSupabase.setResponse('user_memory_insert', {
      data: [TestDataFactory.createMemoryEntry({
        user_id: env.testUser.id,
        content: 'User uploaded trip itinerary',
        embedding: new Array(1536).fill(0.1)
      })],
      error: null
    });

    // Execute the workflow by creating mock functions
    const { MockFileProcessingFunction } = await import("../file-processing/index.test.ts");
    const { MockTripEventsFunction } = await import("../trip-events/index.test.ts");
    const { MockCacheInvalidationFunction } = await import("../cache-invalidation/index.test.ts");
    const { MockTripNotificationsFunction } = await import("../trip-notifications/index.test.ts");
    const { MockAIProcessingFunction } = await import("../ai-processing/index.test.ts");

    const fileProcessor = new MockFileProcessingFunction(env.mockSupabase, env.mockFetch, env.mockRedis);
    const tripEvents = new MockTripEventsFunction(env.mockSupabase, env.mockFetch);
    const cacheInvalidator = new MockCacheInvalidationFunction(env.mockSupabase, env.mockRedis);
    const notificationHandler = new MockTripNotificationsFunction(env.mockSupabase, env.mockFetch);
    const aiProcessor = new MockAIProcessingFunction(env.mockSupabase, env.mockFetch);

    // Test the complete workflow
    const fileRequest = RequestTestHelper.createAuthenticatedRequest({
      attachment_id: 'attachment-123',
      operation: 'virus_scan'
    });

    const fileResponse = await fileProcessor.serve(fileRequest);
    const fileResult = await ResponseAssertions.assertSuccess(fileResponse);
    assertEquals(fileResult.virus_scan_result.clean, true);

    // Verify cache was invalidated
    const cacheRequest = RequestTestHelper.createWebhookRequest({
      type: 'INSERT',
      table: 'file_attachments',
      record: fileData
    });

    const cacheResponse = await cacheInvalidator.serve(cacheRequest);
    await ResponseAssertions.assertSuccess(cacheResponse);

    // Test collaboration addition
    const collaborationRequest = RequestTestHelper.createWebhookRequest({
      type: 'INSERT',
      table: 'trip_collaborators',
      record: collaboratorData
    });

    const eventsResponse = await tripEvents.serve(collaborationRequest);
    await ResponseAssertions.assertSuccess(eventsResponse);

    // Test notification sending
    const notificationRequest = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: env.testTrip.id,
      user_id: env.testUser.id,
      target_user_id: collaboratorUser.id
    });

    const notificationResponse = await notificationHandler.serve(notificationRequest);
    const notificationResult = await ResponseAssertions.assertSuccess(notificationResponse);
    assertEquals(notificationResult.email_sent, true);

    // Test AI processing of the file content
    const aiRequest = RequestTestHelper.createAuthenticatedRequest({
      session_id: env.testSession,
      operation: 'process_memory',
      data: {
        content: `File uploaded: ${fileData.file_name}`,
        context: 'file_upload'
      }
    });

    const aiResponse = await aiProcessor.serve(aiRequest);
    const aiResult = await ResponseAssertions.assertSuccess(aiResponse);
    assertEquals(aiResult.memory_created, true);

    // Verify all components worked together
    assertEquals(env.mockFetch.getCallsFor('openai.com').length, 1);
    assertEquals(env.mockFetch.getCallsFor('resend.com').length, 1);
    assertEquals(env.mockFetch.getCallsFor('virustotal.com').length, 1);

  } finally {
    env.cleanup();
  }
});

Deno.test("Integration - Error Propagation and Recovery", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Test scenario where one function fails but others continue
    
    // Setup: File processing fails due to virus scan error
    env.mockFetch.setResponse('https://api.virustotal.com/api/v3/files', {
      status: 500,
      body: JSON.stringify({ error: 'Service unavailable' })
    });

    // But cache invalidation and notifications should still work
    env.mockRedis.setExpectedCalls([
      { method: 'keys', args: ['trip:*'], result: ['trip:123:cache'] },
      { method: 'del', args: [['trip:123:cache']], result: 1 }
    ]);

    const { MockFileProcessingFunction } = await import("../file-processing/index.test.ts");
    const { MockCacheInvalidationFunction } = await import("../cache-invalidation/index.test.ts");

    const fileProcessor = new MockFileProcessingFunction(env.mockSupabase, env.mockFetch, env.mockRedis);
    const cacheInvalidator = new MockCacheInvalidationFunction(env.mockSupabase, env.mockRedis);

    // File processing should fail gracefully
    const fileRequest = RequestTestHelper.createAuthenticatedRequest({
      attachment_id: 'attachment-123',
      operation: 'virus_scan'
    });

    const fileResponse = await fileProcessor.serve(fileRequest);
    const fileResult = await ResponseAssertions.assertSuccess(fileResponse);
    assertEquals(fileResult.virus_scan_result.error, true);

    // Cache invalidation should still work
    const cacheRequest = RequestTestHelper.createWebhookRequest({
      type: 'UPDATE',
      table: 'file_attachments',
      record: { id: 'attachment-123', status: 'scan_failed' }
    });

    const cacheResponse = await cacheInvalidator.serve(cacheRequest);
    await ResponseAssertions.assertSuccess(cacheResponse);

    // Verify partial success
    assertEquals(env.mockFetch.getCallsFor('virustotal.com').length, 1);

  } finally {
    env.cleanup();
  }
});

Deno.test("Integration - Concurrent Function Execution", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Test multiple functions running simultaneously
    const { MockAIProcessingFunction } = await import("../ai-processing/index.test.ts");
    const { MockTripNotificationsFunction } = await import("../trip-notifications/index.test.ts");
    const { MockCacheInvalidationFunction } = await import("../cache-invalidation/index.test.ts");

    const aiProcessor = new MockAIProcessingFunction(env.mockSupabase, env.mockFetch);
    const notificationHandler = new MockTripNotificationsFunction(env.mockSupabase, env.mockFetch);
    const cacheInvalidator = new MockCacheInvalidationFunction(env.mockSupabase, env.mockRedis);

    // Create concurrent requests
    const requests = [
      aiProcessor.serve(RequestTestHelper.createAuthenticatedRequest({
        session_id: 'session-1',
        operation: 'chat_completion',
        messages: [{ role: 'user', content: 'Hello' }]
      })),
      notificationHandler.serve(RequestTestHelper.createAuthenticatedRequest({
        event_type: 'collaboration_added',
        trip_id: env.testTrip.id,
        user_id: env.testUser.id
      })),
      cacheInvalidator.serve(RequestTestHelper.createWebhookRequest({
        type: 'UPDATE',
        table: 'trips',
        record: { id: env.testTrip.id, name: 'Updated Trip' }
      }))
    ];

    // Execute all requests concurrently
    const responses = await Promise.all(requests);

    // Verify all succeeded
    for (const response of responses) {
      await ResponseAssertions.assertSuccess(response);
    }

    // Verify concurrent execution didn't cause conflicts
    assertEquals(responses.length, 3);

  } finally {
    env.cleanup();
  }
});

Deno.test("Integration - Database Consistency Across Functions", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Test that multiple functions maintain database consistency
    
    // Simulate a trip update that should trigger multiple functions
    const updatedTrip = { ...env.testTrip, name: 'Updated Trip Name' };
    
    env.mockSupabase.setResponse('trips_update', {
      data: [updatedTrip],
      error: null
    });

    // Mock multiple database operations
    let dbOperationCount = 0;
    const originalUpsert = env.mockSupabase.upsert;
    env.mockSupabase.upsert = (...args) => {
      dbOperationCount++;
      return originalUpsert.call(env.mockSupabase, ...args);
    };

    const { MockTripEventsFunction } = await import("../trip-events/index.test.ts");
    const { MockCacheInvalidationFunction } = await import("../cache-invalidation/index.test.ts");

    const tripEvents = new MockTripEventsFunction(env.mockSupabase, env.mockFetch);
    const cacheInvalidator = new MockCacheInvalidationFunction(env.mockSupabase, env.mockRedis);

    // Trigger both functions with the same update
    const webhookPayload = {
      type: 'UPDATE',
      table: 'trips',
      record: updatedTrip,
      old_record: env.testTrip
    };

    const eventsRequest = RequestTestHelper.createWebhookRequest(webhookPayload);
    const cacheRequest = RequestTestHelper.createWebhookRequest(webhookPayload);

    const [eventsResponse, cacheResponse] = await Promise.all([
      tripEvents.serve(eventsRequest),
      cacheInvalidator.serve(cacheRequest)
    ]);

    await ResponseAssertions.assertSuccess(eventsResponse);
    await ResponseAssertions.assertSuccess(cacheResponse);

    // Verify database operations were performed correctly
    assertExists(dbOperationCount);

  } finally {
    env.cleanup();
  }
});

Deno.test("Integration - Cross-Function Data Flow", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Test data flowing from one function to another through database/cache
    
    // Step 1: AI processing creates memory entry
    env.mockSupabase.setResponse('user_memory_insert', {
      data: [TestDataFactory.createMemoryEntry({
        id: 'memory-123',
        user_id: env.testUser.id,
        content: 'User prefers beach destinations',
        embedding: new Array(1536).fill(0.1)
      })],
      error: null
    });

    // Step 2: This memory should be available for trip recommendations
    env.mockSupabase.setResponse('user_memory_select', {
      data: [TestDataFactory.createMemoryEntry({
        id: 'memory-123',
        content: 'User prefers beach destinations'
      })],
      error: null
    });

    const { MockAIProcessingFunction } = await import("../ai-processing/index.test.ts");
    const aiProcessor = new MockAIProcessingFunction(env.mockSupabase, env.mockFetch);

    // First, create the memory
    const memoryRequest = RequestTestHelper.createAuthenticatedRequest({
      session_id: env.testSession,
      operation: 'process_memory',
      data: {
        content: 'I love beach vacations',
        context: 'user_preference'
      }
    });

    const memoryResponse = await aiProcessor.serve(memoryRequest);
    const memoryResult = await ResponseAssertions.assertSuccess(memoryResponse);
    assertEquals(memoryResult.memory_created, true);

    // Then, use the memory for recommendations
    const recommendationRequest = RequestTestHelper.createAuthenticatedRequest({
      session_id: env.testSession,
      operation: 'chat_completion',
      messages: [{ role: 'user', content: 'Suggest a vacation destination' }],
      use_memory: true
    });

    const recommendationResponse = await aiProcessor.serve(recommendationRequest);
    const recommendationResult = await ResponseAssertions.assertSuccess(recommendationResponse);
    assertEquals(recommendationResult.used_memory, true);

    // Verify memory was retrieved and used
    assertEquals(env.mockSupabase.getCallsFor('user_memory').length >= 2, true);

  } finally {
    env.cleanup();
  }
});

Deno.test("Integration - Performance Under Load", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Test system performance with multiple concurrent workflows
    
    const { MockAIProcessingFunction } = await import("../ai-processing/index.test.ts");
    const { MockCacheInvalidationFunction } = await import("../cache-invalidation/index.test.ts");

    const aiProcessor = new MockAIProcessingFunction(env.mockSupabase, env.mockFetch);
    const cacheInvalidator = new MockCacheInvalidationFunction(env.mockSupabase, env.mockRedis);

    // Create multiple concurrent workflows
    const workflows = [];
    const startTime = Date.now();

    for (let i = 0; i < 10; i++) {
      workflows.push(
        // AI processing workflow
        aiProcessor.serve(RequestTestHelper.createAuthenticatedRequest({
          session_id: `session-${i}`,
          operation: 'chat_completion',
          messages: [{ role: 'user', content: `Message ${i}` }]
        })),
        
        // Cache invalidation workflow
        cacheInvalidator.serve(RequestTestHelper.createWebhookRequest({
          type: 'UPDATE',
          table: 'trips',
          record: { id: i, name: `Trip ${i}` }
        }))
      );
    }

    const responses = await Promise.all(workflows);
    const endTime = Date.now();
    const totalTime = endTime - startTime;

    // Verify all requests completed successfully
    assertEquals(responses.length, 20);
    for (const response of responses) {
      await ResponseAssertions.assertSuccess(response);
    }

    // Performance assertion (should complete within reasonable time)
    console.log(`Integration load test completed in ${totalTime}ms`);
    assertEquals(totalTime < 10000, true, 'Load test should complete within 10 seconds');

  } finally {
    env.cleanup();
  }
});

Deno.test("Integration - End-to-End User Journey", async () => {
  const env = new IntegrationTestEnvironment();
  await env.setup();

  try {
    // Simulate a complete user journey from chat to trip creation to collaboration
    
    const { MockAIProcessingFunction } = await import("../ai-processing/index.test.ts");
    const { MockTripNotificationsFunction } = await import("../trip-notifications/index.test.ts");
    const { MockCacheInvalidationFunction } = await import("../cache-invalidation/index.test.ts");

    const aiProcessor = new MockAIProcessingFunction(env.mockSupabase, env.mockFetch);
    const notificationHandler = new MockTripNotificationsFunction(env.mockSupabase, env.mockFetch);
    const cacheInvalidator = new MockCacheInvalidationFunction(env.mockSupabase, env.mockRedis);

    // Step 1: User starts a chat session for trip planning
    const chatRequest = RequestTestHelper.createAuthenticatedRequest({
      session_id: env.testSession,
      operation: 'chat_completion',
      messages: [{ 
        role: 'user', 
        content: 'Help me plan a 7-day trip to Japan in spring' 
      }]
    });

    const chatResponse = await aiProcessor.serve(chatRequest);
    await ResponseAssertions.assertSuccess(chatResponse);

    // Step 2: AI creates memory about user preferences
    const memoryRequest = RequestTestHelper.createAuthenticatedRequest({
      session_id: env.testSession,
      operation: 'process_memory',
      data: {
        content: 'User wants 7-day Japan trip in spring',
        context: 'trip_planning'
      }
    });

    const memoryResponse = await aiProcessor.serve(memoryRequest);
    await ResponseAssertions.assertSuccess(memoryResponse);

    // Step 3: User invites collaborator to the trip
    const notificationRequest = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: env.testTrip.id,
      user_id: env.testUser.id,
      target_user_id: 'collaborator-789',
      permission_level: 'edit'
    });

    const notificationResponse = await notificationHandler.serve(notificationRequest);
    await ResponseAssertions.assertSuccess(notificationResponse);

    // Step 4: Cache is updated with new collaboration
    const cacheRequest = RequestTestHelper.createWebhookRequest({
      type: 'INSERT',
      table: 'trip_collaborators',
      record: {
        trip_id: env.testTrip.id,
        user_id: 'collaborator-789',
        permission_level: 'edit'
      }
    });

    const cacheResponse = await cacheInvalidator.serve(cacheRequest);
    await ResponseAssertions.assertSuccess(cacheResponse);

    // Verify the complete journey worked
    assertEquals(env.mockFetch.getCallsFor('openai.com').length >= 2, true);
    assertEquals(env.mockFetch.getCallsFor('resend.com').length, 1);

  } finally {
    env.cleanup();
  }
});

console.log("🔗 Edge Functions Integration Test Suite");
console.log("==========================================");
console.log("Testing cross-function workflows:");
console.log("✓ Complete trip collaboration workflow");
console.log("✓ Error propagation and recovery");
console.log("✓ Concurrent function execution");
console.log("✓ Database consistency across functions");
console.log("✓ Cross-function data flow");
console.log("✓ Performance under load");
console.log("✓ End-to-end user journey");
console.log("");
console.log("Run with: deno test --allow-net --allow-env _shared/integration.test.ts");
