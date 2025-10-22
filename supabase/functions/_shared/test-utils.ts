/**
 * Shared test utilities for Edge Functions
 * 
 * Provides mocking capabilities, test data factories, and assertion helpers
 * for Edge Function testing.
 * 
 * @module test-utils
 */

import { assertEquals, assertExists, assertRejects } from "https://deno.land/std@0.208.0/assert/mod.ts";
import { stub, Stub } from "https://deno.land/std@0.208.0/testing/mock.ts";

// Test configuration
export const TEST_CONFIG = {
  SUPABASE_URL: 'https://test.supabase.co',
  SUPABASE_SERVICE_ROLE_KEY: 'test-service-role-key',
  SUPABASE_ANON_KEY: 'test-anon-key',
  WEBHOOK_SECRET: 'test-webhook-secret',
  OPENAI_API_KEY: 'test-openai-key',
  REDIS_URL: 'redis://localhost:6379',
  REDIS_PASSWORD: 'test-password',
  RESEND_API_KEY: 'test-resend-key',
  MAX_FILE_SIZE: '50000000'
};

// Mock data factories
export const TestDataFactory = {
  /**
   * Creates a test user object
   */
  createUser: (overrides: Partial<any> = {}) => ({
    id: 'test-user-123',
    email: 'test@example.com',
    raw_user_meta_data: {
      full_name: 'Test User'
    },
    ...overrides
  }),

  /**
   * Creates a test trip object
   */
  createTrip: (overrides: Partial<any> = {}) => ({
    id: 123,
    name: 'Test Trip to Paris',
    destination: 'Paris, France',
    start_date: '2025-06-15',
    end_date: '2025-06-22',
    user_id: 'test-user-123',
    ...overrides
  }),

  /**
   * Creates a test file attachment object
   */
  createFileAttachment: (overrides: Partial<any> = {}) => ({
    id: 'test-file-456',
    user_id: 'test-user-123',
    trip_id: 123,
    filename: 'test-image.jpg',
    original_filename: 'test-image.jpg',
    file_size: 1024000,
    mime_type: 'image/jpeg',
    file_path: 'uploads/test-image.jpg',
    bucket_name: 'attachments',
    upload_status: 'uploading',
    virus_scan_status: 'pending',
    virus_scan_result: {},
    metadata: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides
  }),

  /**
   * Creates a test trip collaborator object
   */
  createTripCollaborator: (overrides: Partial<any> = {}) => ({
    id: 1,
    trip_id: 123,
    user_id: 'test-collaborator-456',
    permission_level: 'view',
    added_by: 'test-user-123',
    added_at: new Date().toISOString(),
    ...overrides
  }),

  /**
   * Creates a test webhook payload
   */
  createWebhookPayload: (table: string, type: 'INSERT' | 'UPDATE' | 'DELETE', record: any, oldRecord?: any) => ({
    type,
    table,
    record,
    old_record: oldRecord,
    schema: 'public'
  }),

  /**
   * Creates a test AI processing event
   */
  createAIProcessingEvent: (overrides: Partial<any> = {}) => ({
    event: 'chat.message.process',
    message_id: 789,
    session_id: 'test-session-123',
    user_id: 'test-user-123',
    trip_id: 123,
    content: 'I want to book a budget hotel in Paris',
    timestamp: new Date().toISOString(),
    metadata: {},
    ...overrides
  }),

  /**
   * Creates a test trip event
   */
  createTripEvent: (overrides: Partial<any> = {}) => ({
    event: 'trip.collaborator.added',
    trip_id: 123,
    user_id: 'test-collaborator-456',
    added_by: 'test-user-123',
    permission_level: 'view',
    timestamp: new Date().toISOString(),
    operation: 'INSERT',
    data: {},
    ...overrides
  }),

  /**
   * Creates a test chat message object
   */
  createChatMessage: (overrides: Partial<any> = {}) => ({
    id: 'msg-123',
    content: 'Test message content',
    role: 'user',
    session_id: 'test-session-123',
    user_id: 'test-user-123',
    created_at: new Date().toISOString(),
    ...overrides
  }),

  /**
   * Creates a test memory entry object
   */
  createMemoryEntry: (overrides: Partial<any> = {}) => ({
    id: 'memory-123',
    user_id: 'test-user-123',
    content: 'Test memory content',
    embedding: new Array(1536).fill(0.1),
    metadata: {},
    created_at: new Date().toISOString(),
    ...overrides
  })
};

// Mock implementations
export class MockSupabase {
  private responses: Map<string, any> = new Map();
  public calls: Array<{ method: string; args: any[] }> = [];

  /**
   * Sets up mock responses for database operations
   */
  setResponse(key: string, response: any) {
    this.responses.set(key, response);
  }

  /**
   * Mock from() method
   */
  from(table: string) {
    this.calls.push({ method: 'from', args: [table] });
    return {
      select: (columns: string) => {
        this.calls.push({ method: 'select', args: [columns] });
        return this._createQueryBuilder(`${table}_select`);
      },
      insert: (data: any) => {
        this.calls.push({ method: 'insert', args: [data] });
        return this._createQueryBuilder(`${table}_insert`);
      },
      update: (data: any) => {
        this.calls.push({ method: 'update', args: [data] });
        return this._createQueryBuilder(`${table}_update`);
      },
      delete: () => {
        this.calls.push({ method: 'delete', args: [] });
        return this._createQueryBuilder(`${table}_delete`);
      }
    };
  }

  /**
   * Mock storage operations
   */
  get storage() {
    return {
      from: (bucket: string) => ({
        download: (path: string) => {
          this.calls.push({ method: 'storage.download', args: [bucket, path] });
          const response = this.responses.get(`storage_download_${bucket}`) || {
            data: new Blob(['test file content']),
            error: null
          };
          return Promise.resolve(response);
        },
        upload: (path: string, data: any, options?: any) => {
          this.calls.push({ method: 'storage.upload', args: [bucket, path, data, options] });
          const response = this.responses.get(`storage_upload_${bucket}`) || {
            data: { path },
            error: null
          };
          return Promise.resolve(response);
        }
      })
    };
  }

  /**
   * Mock auth operations
   */
  get auth() {
    return {
      getUser: (token: string) => {
        this.calls.push({ method: 'auth.getUser', args: [token] });
        const response = this.responses.get('auth_getUser') || {
          data: { user: TestDataFactory.createUser() },
          error: null
        };
        return Promise.resolve(response);
      }
    };
  }

  private _createQueryBuilder(key: string) {
    return {
      eq: (column: string, value: any) => {
        this.calls.push({ method: 'eq', args: [column, value] });
        return this._createQueryBuilder(`${key}_eq`);
      },
      is: (column: string, value: any) => {
        this.calls.push({ method: 'is', args: [column, value] });
        return this._createQueryBuilder(`${key}_is`);
      },
      lt: (column: string, value: any) => {
        this.calls.push({ method: 'lt', args: [column, value] });
        return this._createQueryBuilder(`${key}_lt`);
      },
      ilike: (column: string, value: any) => {
        this.calls.push({ method: 'ilike', args: [column, value] });
        return this._createQueryBuilder(`${key}_ilike`);
      },
      limit: (count: number) => {
        this.calls.push({ method: 'limit', args: [count] });
        return this._createQueryBuilder(`${key}_limit`);
      },
      single: () => {
        this.calls.push({ method: 'single', args: [] });
        const response = this.responses.get(key) || {
          data: {},
          error: null
        };
        return Promise.resolve(response);
      },
      then: (callback: (result: any) => void) => {
        const response = this.responses.get(key) || {
          data: [],
          error: null
        };
        return Promise.resolve(response).then(callback);
      }
    };
  }

  /**
   * Clears all recorded calls
   */
  clearCalls() {
    this.calls = [];
  }

  /**
   * Gets calls for a specific method
   */
  getCallsFor(method: string) {
    return this.calls.filter(call => call.method === method);
  }
}

/**
 * Mock Redis client for testing cache operations
 */
export class MockRedis {
  private storage: Map<string, string> = new Map();
  public calls: Array<{ method: string; args: any[] }> = [];
  private expectedCalls: Array<{ method: string; args: any[]; result: any }> = [];

  connect() {
    this.calls.push({ method: 'connect', args: [] });
    return Promise.resolve(this);
  }

  keys(pattern: string) {
    this.calls.push({ method: 'keys', args: [pattern] });
    
    // Simple pattern matching for testing
    const keys = Array.from(this.storage.keys()).filter(key => {
      if (pattern.endsWith('*')) {
        const prefix = pattern.slice(0, -1);
        return key.startsWith(prefix);
      }
      return key === pattern;
    });
    
    return Promise.resolve(keys);
  }

  del(...keys: string[]) {
    this.calls.push({ method: 'del', args: keys });
    let deleted = 0;
    keys.forEach(key => {
      if (this.storage.has(key)) {
        this.storage.delete(key);
        deleted++;
      }
    });
    return Promise.resolve(deleted);
  }

  set(key: string, value: string) {
    this.calls.push({ method: 'set', args: [key, value] });
    const expectedResult = this.findExpectedCall('set', [key, value]);
    if (expectedResult !== undefined) {
      if (expectedResult === 'OK') {
        this.storage.set(key, value);
      }
      return expectedResult;
    }
    this.storage.set(key, value);
    return 'OK';
  }

  get(key: string) {
    this.calls.push({ method: 'get', args: [key] });
    const expectedResult = this.findExpectedCall('get', [key]);
    if (expectedResult !== undefined) {
      return expectedResult;
    }
    return this.storage.get(key) || null;
  }

  quit() {
    this.calls.push({ method: 'quit', args: [] });
    return Promise.resolve();
  }

  clearCalls() {
    this.calls = [];
  }

  setExpectedCalls(calls: Array<{ method: string; args: any[]; result: any }>) {
    this.expectedCalls = calls;
  }

  addTestKeys(prefix: string, count: number) {
    for (let i = 0; i < count; i++) {
      this.storage.set(`${prefix}${i}`, `value${i}`);
    }
  }

  private findExpectedCall(method: string, args: any[]): any {
    const call = this.expectedCalls.find(
      expectedCall => expectedCall.method === method && 
      JSON.stringify(expectedCall.args) === JSON.stringify(args)
    );
    return call?.result;
  }
}

/**
 * Mock fetch function for testing external API calls
 */
export class MockFetch {
  private responses: Map<string, Response> = new Map();
  public calls: Array<{ url: string; options?: RequestInit }> = [];

  setResponse(url: string, response: { status?: number; statusText?: string; headers?: Record<string, string>; body?: string }) {
    const mockResponse = new Response(
      response.body || JSON.stringify({ success: true }),
      {
        status: response.status || 200,
        statusText: response.statusText || 'OK',
        headers: response.headers || { 'Content-Type': 'application/json' }
      }
    );
    this.responses.set(url, mockResponse);
  }

  fetch = (url: string | Request, options?: RequestInit) => {
    const urlString = typeof url === 'string' ? url : url.url;
    this.calls.push({ url: urlString, options });
    
    const response = this.responses.get(urlString) || new Response(
      JSON.stringify({ error: 'Mock response not found' }),
      { status: 404 }
    );
    
    return Promise.resolve(response);
  };

  clearCalls() {
    this.calls = [];
  }

  getCallsFor(urlPattern: string) {
    return this.calls.filter(call => call.url.includes(urlPattern));
  }
}

/**
 * Test environment setup and cleanup utilities
 */
export class TestEnvironment {
  private originalEnv: Record<string, string> = {};
  private stubs: Stub[] = [];

  /**
   * Sets up test environment with mock configuration
   */
  setup() {
    // Store original environment variables
    Object.keys(TEST_CONFIG).forEach(key => {
      this.originalEnv[key] = Deno.env.get(key) || '';
      Deno.env.set(key, TEST_CONFIG[key as keyof typeof TEST_CONFIG]);
    });
  }

  /**
   * Cleans up test environment
   */
  cleanup() {
    // Restore original environment variables
    Object.keys(this.originalEnv).forEach(key => {
      if (this.originalEnv[key]) {
        Deno.env.set(key, this.originalEnv[key]);
      } else {
        Deno.env.delete(key);
      }
    });

    // Restore all stubs
    this.stubs.forEach(stub => stub.restore());
    this.stubs = [];
  }

  /**
   * Creates a stub and tracks it for cleanup
   */
  stub<T>(object: T, property: keyof T, value?: any): Stub<T> {
    const stubInstance = stub(object, property, value);
    this.stubs.push(stubInstance as any);
    return stubInstance;
  }
}

/**
 * Request test helpers
 */
export class RequestTestHelper {
  /**
   * Creates a test Request object
   */
  static createRequest(options: {
    method?: string;
    url?: string;
    headers?: Record<string, string>;
    body?: any;
  } = {}) {
    const {
      method = 'POST',
      url = 'https://test.supabase.co/functions/v1/test',
      headers = { 'Content-Type': 'application/json' },
      body = {}
    } = options;

    return new Request(url, {
      method,
      headers,
      body: method !== 'GET' && method !== 'OPTIONS' ? JSON.stringify(body) : undefined
    });
  }

  /**
   * Creates a test webhook request
   */
  static createWebhookRequest(payload: any, secret = 'test-webhook-secret') {
    return this.createRequest({
      headers: {
        'Content-Type': 'application/json',
        'x-webhook-secret': secret
      },
      body: payload
    });
  }

  /**
   * Creates an authenticated request
   */
  static createAuthenticatedRequest(payload: any, token = 'test-auth-token') {
    return this.createRequest({
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: payload
    });
  }

  /**
   * Creates an OPTIONS request for CORS testing
   */
  static createOptionsRequest() {
    return this.createRequest({
      method: 'OPTIONS'
    });
  }
}

/**
 * Response assertion helpers
 */
export class ResponseAssertions {
  /**
   * Asserts response is successful
   */
  static async assertSuccess(response: Response, expectedData?: any) {
    assertEquals(response.status, 200);
    assertEquals(response.headers.get('Content-Type'), 'application/json');
    
    const data = await response.json();
    assertEquals(data.success, true);
    
    if (expectedData) {
      Object.keys(expectedData).forEach(key => {
        assertEquals(data[key], expectedData[key]);
      });
    }
    
    return data;
  }

  /**
   * Asserts response is an error
   */
  static async assertError(response: Response, expectedStatus: number, expectedError?: string) {
    assertEquals(response.status, expectedStatus);
    
    const data = await response.json();
    assertExists(data.error);
    
    if (expectedError) {
      assertEquals(data.error, expectedError);
    }
    
    return data;
  }

  /**
   * Asserts CORS headers are present
   */
  static assertCorsHeaders(response: Response) {
    assertEquals(response.headers.get('Access-Control-Allow-Origin'), '*');
    assertExists(response.headers.get('Access-Control-Allow-Methods'));
    assertExists(response.headers.get('Access-Control-Allow-Headers'));
  }

  /**
   * Asserts response time is reasonable
   */
  static assertResponseTime(startTime: number, maxMs = 5000) {
    const responseTime = Date.now() - startTime;
    if (responseTime > maxMs) {
      throw new Error(`Response time ${responseTime}ms exceeds maximum ${maxMs}ms`);
    }
    return responseTime;
  }
}

/**
 * Edge Function test runner with setup
 */
export class EdgeFunctionTester {
  private mockSupabase: MockSupabase;
  private mockRedis: MockRedis;
  private mockFetch: MockFetch;
  private testEnv: TestEnvironment;

  constructor() {
    this.mockSupabase = new MockSupabase();
    this.mockRedis = new MockRedis();
    this.mockFetch = new MockFetch();
    this.testEnv = new TestEnvironment();
  }

  /**
   * Sets up test environment
   */
  async setup() {
    this.testEnv.setup();
    
    // Mock global fetch
    this.testEnv.stub(globalThis, 'fetch', this.mockFetch.fetch);
    
    return {
      mockSupabase: this.mockSupabase,
      mockRedis: this.mockRedis,
      mockFetch: this.mockFetch,
      testEnv: this.testEnv
    };
  }

  /**
   * Cleans up test environment
   */
  cleanup() {
    this.testEnv.cleanup();
    this.mockSupabase.clearCalls();
    this.mockRedis.clearCalls();
    this.mockFetch.clearCalls();
  }

  /**
   * Runs a test with setup and cleanup
   */
  async runTest(testFn: (mocks: {
    mockSupabase: MockSupabase;
    mockRedis: MockRedis;
    mockFetch: MockFetch;
  }) => Promise<void>) {
    const mocks = await this.setup();
    try {
      await testFn({
        mockSupabase: this.mockSupabase,
        mockRedis: this.mockRedis,
        mockFetch: this.mockFetch
      });
    } finally {
      this.cleanup();
    }
  }
}

// Export commonly used assertions
export { assertEquals, assertExists, assertRejects };
