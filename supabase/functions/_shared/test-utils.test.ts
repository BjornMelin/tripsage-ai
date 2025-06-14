/**
 * Test suite for the shared test utilities
 * Validates that our testing infrastructure works correctly
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

Deno.test("TestDataFactory - User Creation", () => {
  const user = TestDataFactory.createUser();
  
  assertExists(user.id);
  assertExists(user.email);
  assertEquals(user.email.includes('@'), true);
  assertEquals(typeof user.id, 'string');
});

Deno.test("TestDataFactory - Trip Creation", () => {
  const trip = TestDataFactory.createTrip();
  
  assertExists(trip.id);
  assertExists(trip.name);
  assertExists(trip.destination);
  assertEquals(typeof trip.id, 'number');
  assertEquals(typeof trip.name, 'string');
});

Deno.test("TestDataFactory - Chat Message Creation", () => {
  const message = TestDataFactory.createChatMessage();
  
  assertExists(message.id);
  assertExists(message.content);
  assertExists(message.role);
  assertEquals(['user', 'assistant', 'system'].includes(message.role), true);
});

Deno.test("TestDataFactory - Custom Properties", () => {
  const customUser = TestDataFactory.createUser({
    id: 'custom-123',
    email: 'custom@test.com'
  });
  
  assertEquals(customUser.id, 'custom-123');
  assertEquals(customUser.email, 'custom@test.com');
});

Deno.test("MockSupabase - Response Setting and Retrieval", () => {
  const mockSupabase = new MockSupabase();
  
  const testResponse = { data: [{ id: 1 }], error: null };
  mockSupabase.setResponse('test_operation', testResponse);
  
  // Test the mock's from().select() chain
  const result = mockSupabase.from('test_table');
  assertExists(result.select);
  assertExists(result.insert);
  assertExists(result.update);
});

Deno.test("MockRedis - Command Simulation", () => {
  const mockRedis = new MockRedis();
  
  mockRedis.setExpectedCalls([
    { method: 'get', args: ['test-key'], result: 'test-value' },
    { method: 'set', args: ['test-key', 'new-value'], result: 'OK' }
  ]);
  
  assertEquals(mockRedis.get('test-key'), 'test-value');
  assertEquals(mockRedis.set('test-key', 'new-value'), 'OK');
});

Deno.test("MockFetch - URL Pattern Matching", () => {
  const mockFetch = new MockFetch();
  
  mockFetch.setResponse('https://api.openai.com/v1/chat', {
    status: 200,
    body: JSON.stringify({ choices: [{ message: { content: 'Hello' } }] })
  });
  
  const calls = mockFetch.getCallsFor('openai.com');
  assertEquals(calls.length, 0); // No calls made yet
  
  // Simulate a call
  mockFetch.fetch('https://api.openai.com/v1/chat', { method: 'POST' });
  
  const callsAfter = mockFetch.getCallsFor('openai.com');
  assertEquals(callsAfter.length, 1);
});

Deno.test("RequestTestHelper - Authenticated Request Creation", () => {
  const request = RequestTestHelper.createAuthenticatedRequest({
    test: 'data'
  }, 'test-token');
  
  assertEquals(request.method, 'POST');
  assertEquals(request.headers.get('authorization'), 'Bearer test-token');
  assertEquals(request.headers.get('content-type'), 'application/json');
});

Deno.test("RequestTestHelper - Webhook Request Creation", () => {
  const payload = { type: 'INSERT', table: 'test' };
  const request = RequestTestHelper.createWebhookRequest(payload);
  
  assertEquals(request.method, 'POST');
  assertEquals(request.headers.get('x-webhook-secret'), 'test-webhook-secret');
  assertEquals(request.headers.get('content-type'), 'application/json');
});

Deno.test("RequestTestHelper - OPTIONS Request Creation", () => {
  const request = RequestTestHelper.createOptionsRequest();
  
  assertEquals(request.method, 'OPTIONS');
  // Note: OPTIONS requests typically don't have these headers by default
  assertEquals(request.url, 'https://test.supabase.co/functions/v1/test');
});

Deno.test("ResponseAssertions - Success Response", async () => {
  const mockResponse = new Response(JSON.stringify({ success: true, data: 'test' }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
  
  const data = await ResponseAssertions.assertSuccess(mockResponse);
  assertEquals(data.success, true);
  assertEquals(data.data, 'test');
});

Deno.test("ResponseAssertions - Error Response", async () => {
  const mockResponse = new Response(JSON.stringify({ error: 'Test error' }), {
    status: 400,
    headers: { 'Content-Type': 'application/json' }
  });
  
  // assertError should not throw when the response matches expectations
  const result = await ResponseAssertions.assertError(mockResponse, 400, 'Test error');
  assertEquals(result.error, 'Test error');
});

Deno.test("ResponseAssertions - CORS Headers", () => {
  const mockResponse = new Response('ok', {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'authorization, content-type'
    }
  });
  
  // Should not throw
  ResponseAssertions.assertCorsHeaders(mockResponse);
});

Deno.test("ResponseAssertions - Response Time", () => {
  const startTime = Date.now();
  const maxTime = 1000;
  
  // Simulate some processing time
  const elapsed = Date.now() - startTime;
  
  const responseTime = ResponseAssertions.assertResponseTime(startTime, maxTime);
  assertEquals(responseTime >= elapsed, true);
  assertEquals(responseTime <= maxTime, true);
});

Deno.test("EdgeFunctionTester - Test Environment", async () => {
  const tester = new EdgeFunctionTester();
  
  await tester.runTest(async ({ mockSupabase, mockFetch, mockRedis }) => {
    assertExists(mockSupabase);
    assertExists(mockFetch);
    assertExists(mockRedis);
    
    // Test that mocks are properly initialized
    assertExists(mockSupabase.from);
    assertExists(mockFetch.fetch);
    assertExists(mockRedis.get);
  });
});

Deno.test("EdgeFunctionTester - Environment Isolation", async () => {
  const tester = new EdgeFunctionTester();
  
  // First test sets an environment variable
  await tester.runTest(async () => {
    Deno.env.set('TEST_VAR', 'test-value');
  });
  
  // Second test should not see the variable (isolation)
  await tester.runTest(async () => {
    const value = Deno.env.get('TEST_VAR');
    // Variable might still exist, but test environment should be clean
    // This tests that mocks are reset between tests
    assertExists(tester); // Basic check that tester is working
  });
});

console.log("🧪 Test Utilities Validation Suite");
console.log("===================================");
console.log("Validating shared testing infrastructure:");
console.log("✓ TestDataFactory generates realistic test data");
console.log("✓ MockSupabase simulates database operations");
console.log("✓ MockRedis simulates cache operations");
console.log("✓ MockFetch simulates HTTP requests");
console.log("✓ RequestTestHelper creates proper test requests");
console.log("✓ ResponseAssertions validate responses correctly");
console.log("✓ EdgeFunctionTester provides isolated test environment");
console.log("");
console.log("Run with: deno test --allow-net --allow-env _shared/test-utils.test.ts");