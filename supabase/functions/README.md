# TripSage Edge Functions Test Suite

This directory contains comprehensive test coverage for all Supabase Edge Functions used in the TripSage platform.

## 📁 Structure

```text
functions/
├── _shared/                    # Shared testing utilities
│   ├── test-utils.ts          # Core testing infrastructure
│   ├── test-utils.test.ts     # Tests for test utilities
│   └── integration.test.ts    # Cross-function integration tests
├── ai-processing/             # AI processing function
│   ├── index.ts              # Function implementation
│   └── index.test.ts         # Comprehensive test suite
├── trip-events/              # Trip collaboration events
│   ├── index.ts              # Function implementation
│   └── index.test.ts         # Comprehensive test suite
├── file-processing/          # File upload and processing
│   ├── index.ts              # Function implementation
│   └── index.test.ts         # Comprehensive test suite
├── cache-invalidation/       # Redis cache management
│   ├── index.ts              # Function implementation
│   └── index.test.ts         # Comprehensive test suite
├── trip-notifications/       # Email and webhook notifications
│   ├── index.ts              # Function implementation
│   └── index.test.ts         # Comprehensive test suite
├── deno.json                 # Deno configuration and tasks
├── import_map.json           # Import mappings
├── run-tests.ts              # Test runner script
└── README.md                 # This file
```

## 🧪 Test Coverage

Each Edge Function has **90%+ test coverage** including:

### Core Functionality Tests

- ✅ HTTP request/response handling
- ✅ CORS preflight requests
- ✅ Authentication and authorization
- ✅ Input validation and sanitization
- ✅ Business logic execution
- ✅ Database operations
- ✅ External API integrations

### Edge Cases & Error Handling

- ✅ Invalid input handling
- ✅ Authentication failures
- ✅ Database connection errors
- ✅ External service failures
- ✅ Network timeouts
- ✅ Malformed requests
- ✅ Resource not found scenarios

### Performance & Security

- ✅ Response time validation
- ✅ Concurrent request handling
- ✅ Memory usage optimization
- ✅ Security header verification
- ✅ Rate limiting compliance
- ✅ SQL injection prevention

### Integration Workflows

- ✅ Cross-function data flow
- ✅ Database consistency
- ✅ Cache invalidation chains
- ✅ Notification pipelines
- ✅ Error propagation
- ✅ End-to-end user journeys

## Available Functions

### 1. AI Processing (`ai-processing`)

Handles AI-powered chat completions, memory processing, and embedding generation.

**Features:**

- OpenAI API integration for chat completions
- User memory creation and retrieval
- Embedding generation for semantic search
- User preference extraction and storage

**Test Coverage:**

- Chat message processing workflows
- Memory embedding operations
- User preference extraction
- OpenAI API integration testing
- Error handling and edge cases

### 2. Trip Events (`trip-events`)

Processes trip collaboration events and webhook notifications.

**Features:**

- Database webhook event handling
- Notification creation for trip changes
- Email integration for collaboration events
- Real-time event processing

**Test Coverage:**

- Webhook event processing
- Notification creation workflows
- Email integration testing
- Database trigger simulation
- Collaboration event handling

### 3. File Processing (`file-processing`)

Handles file upload processing, virus scanning, and image optimization.

**Features:**

- Virus scanning integration
- Image resizing and optimization
- File metadata extraction
- Storage bucket management

**Test Coverage:**

- File upload processing
- Virus scan operations
- Image optimization workflows
- Storage integration testing
- Security validation

### 4. Cache Invalidation (`cache-invalidation`)

Manages Redis/DragonflyDB cache invalidation and search cache cleanup.

**Features:**

- Redis cache pattern matching
- Bulk cache key deletion
- Search cache table cleanup
- Webhook-triggered invalidation

**Test Coverage:**

- Redis cache operations
- Pattern-based invalidation
- Webhook event handling
- Performance testing
- Concurrent invalidation

### 5. Trip Notifications (`trip-notifications`)

Handles email notifications and webhook delivery for trip events.

**Features:**

- Email notifications via Resend API
- Webhook notifications to external services
- Template-based email generation
- User and trip data integration

**Test Coverage:**

- Email notification delivery
- Webhook notification sending
- Template generation testing
- User data retrieval
- Integration workflows

## 🚀 Running Tests

### Prerequisites

Ensure you have Deno installed:

```bash
curl -fsSL https://deno.land/install.sh | sh
```

### Quick Start

```bash
# Run all tests
deno task test

# Run with coverage
deno task test:coverage

# Watch mode for development
deno task test:watch
```

### Individual Function Tests

```bash
# AI Processing tests
deno task test:ai

# Trip Events tests
deno task test:trip-events

# File Processing tests
deno task test:file-processing

# Cache Invalidation tests
deno task test:cache

# Notifications tests
deno task test:notifications

# Integration tests
deno task test:integration

# Test utilities validation
deno task test:utils
```

### Advanced Test Runner

```bash
# Use the comprehensive test runner
deno run --allow-net --allow-env --allow-read --allow-write run-tests.ts
```

This will:

- Run all test suites sequentially
- Generate detailed reports
- Calculate coverage estimates
- Save results to `test-results.json`
- Provide performance metrics

## 📊 Coverage Reports

### Generating Coverage

```bash
# Generate LCOV coverage report
deno task coverage:generate

# Generate HTML coverage report
deno task coverage:html
```

### Coverage Goals

- **Individual Functions**: 90%+ coverage each
- **Integration Tests**: Complete workflow coverage
- **Error Scenarios**: All error paths tested
- **Performance**: Response time validation
- **Security**: Authentication and authorization

## 🛠 Testing Infrastructure

### MockSupabase

Simulates Supabase database operations:

```typescript
const mockSupabase = new MockSupabase();
mockSupabase.setResponse("trips_select_eq_single", {
  data: TestDataFactory.createTrip(),
  error: null,
});
```

### MockRedis

Simulates Redis cache operations:

```typescript
const mockRedis = new MockRedis();
mockRedis.setExpectedCalls([{ method: "get", args: ["key"], result: "value" }]);
```

### MockFetch

Simulates external API calls:

```typescript
const mockFetch = new MockFetch();
mockFetch.setResponse("https://api.openai.com/v1/chat", {
  status: 200,
  body: JSON.stringify({ response: "Hello" }),
});
```

### TestDataFactory

Generates realistic test data:

```typescript
const user = TestDataFactory.createUser();
const trip = TestDataFactory.createTrip();
const message = TestDataFactory.createChatMessage();
```

### RequestTestHelper

Creates proper test requests:

```typescript
const request = RequestTestHelper.createAuthenticatedRequest(data, token);
const webhook = RequestTestHelper.createWebhookRequest(payload);
```

### ResponseAssertions

Validates responses:

```typescript
const data = await ResponseAssertions.assertSuccess(response);
await ResponseAssertions.assertError(response, 400, "Error message");
ResponseAssertions.assertCorsHeaders(response);
```

## 🔄 Development Workflow

### Adding New Tests

1. **Create test file**: `function-name/index.test.ts`
2. **Import utilities**: Use shared test infrastructure
3. **Mock dependencies**: Set up required mocks
4. **Write test cases**: Cover all scenarios
5. **Run tests**: Verify coverage and functionality

### Test Structure Template

```typescript
import {
  assertEquals,
  assertExists,
  TestDataFactory,
  EdgeFunctionTester,
} from "../_shared/test-utils.ts";

Deno.test("Function Name - Success Case", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup mocks
    mockSupabase.setResponse("operation", { data: [], error: null });

    // Create function instance
    const func = new MockFunctionClass(mockSupabase, mockFetch);

    // Execute test
    const request = RequestTestHelper.createAuthenticatedRequest(data);
    const response = await func.serve(request);

    // Assertions
    const result = await ResponseAssertions.assertSuccess(response);
    assertEquals(result.expected, true);
  });
});
```

## 📈 Performance Benchmarks

### Response Time Targets

- **Simple operations**: < 500ms
- **Database queries**: < 1000ms
- **External API calls**: < 2000ms
- **File processing**: < 5000ms
- **AI operations**: < 10000ms

### Concurrent Load Testing

Integration tests include scenarios with:

- 10+ concurrent requests
- Multiple function interactions
- Database consistency validation
- Error isolation verification

## 🔒 Security Testing

### Authentication Tests

- Valid JWT token handling
- Invalid token rejection
- Missing authorization headers
- Token expiration scenarios

### Input Validation

- SQL injection prevention
- XSS attack mitigation
- File upload security
- Request size limits

### CORS Configuration

- Proper CORS headers
- Origin validation
- Method restrictions
- Credentials handling

## Configuration

### Environment Variables

All functions require the following base environment variables:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

# Webhook Security
WEBHOOK_SECRET=your_webhook_secret
```

### Function-Specific Environment Variables

#### Trip Notifications

```bash
# Email Service (optional)
RESEND_API_KEY=your_resend_api_key

# External Webhook (optional)
NOTIFICATION_WEBHOOK_URL=your_notification_webhook_url
```

#### File Processing

```bash
# Storage Configuration
STORAGE_BUCKET=attachments
MAX_FILE_SIZE=50000000

# Virus Scanning (optional)
VIRUS_SCAN_API_KEY=your_virus_scan_api_key
CLOUDFLARE_AI_TOKEN=your_cloudflare_token
```

#### Cache Invalidation

```bash
# Redis/DragonflyDB Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password

# Cache Webhook (optional)
CACHE_WEBHOOK_URL=your_cache_webhook_url
```

## Database Triggers

### Setting up Webhooks

To enable automatic processing, set up database webhooks for these tables:

1. **trip_collaborators** → trip-notifications
2. **file_attachments** → file-processing
3. **All tables** → cache-invalidation

Example webhook configuration:

```sql
-- Enable webhooks for trip_collaborators
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;

-- Function to send webhook
CREATE OR REPLACE FUNCTION send_webhook_notification()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('webhook_channel', json_build_object(
    'type', TG_OP,
    'table', TG_TABLE_NAME,
    'record', row_to_json(NEW),
    'old_record', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END,
    'schema', TG_TABLE_SCHEMA
  )::text);
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER trip_collaborators_webhook
  AFTER INSERT OR UPDATE OR DELETE ON trip_collaborators
  FOR EACH ROW EXECUTE FUNCTION send_webhook_notification();
```

## Deployment

### Using Supabase CLI

1. **Deploy all functions:**

   ```bash
   supabase functions deploy
   ```

2. **Deploy specific function:**

   ```bash
   supabase functions deploy trip-notifications
   supabase functions deploy file-processing
   supabase functions deploy cache-invalidation
   ```

3. **Set environment variables:**

   ```bash
   supabase secrets set RESEND_API_KEY=your_key
   supabase secrets set REDIS_URL=your_redis_url
   # ... other secrets
   ```

### Testing Functions

1. **Test trip notifications:**

   ```bash
   curl -X POST https://your-project.supabase.co/functions/v1/trip-notifications \
     -H "Authorization: Bearer your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "collaboration_added",
       "trip_id": 123,
       "user_id": "user-uuid",
       "target_user_id": "target-uuid",
       "permission_level": "view"
     }'
   ```

2. **Test file processing:**

   ```bash
   curl -X POST https://your-project.supabase.co/functions/v1/file-processing \
     -H "Authorization: Bearer your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "file_id": "file-uuid",
       "operation": "process_all"
     }'
   ```

3. **Test cache invalidation:**

   ```bash
   curl -X POST https://your-project.supabase.co/functions/v1/cache-invalidation \
     -H "Authorization: Bearer your_token" \
     -H "Content-Type: application/json" \
     -d '{
       "cache_type": "all",
       "patterns": ["trip:*", "search:*"],
       "reason": "Manual cleanup"
     }'
   ```

## Monitoring and Logging

All functions include comprehensive logging and error handling:

- Request validation and authentication
- Detailed operation logging
- Error reporting and recovery
- Performance metrics (processing times)

Monitor function logs through the Supabase Dashboard or CLI:

```bash
supabase functions logs trip-notifications
```

## Security Considerations

1. **Authentication**: All functions validate JWT tokens
2. **Webhook Security**: Webhook endpoints verify secret tokens
3. **Input Validation**: All requests are validated for required fields
4. **Error Handling**: Sensitive information is not exposed in error responses
5. **Rate Limiting**: Consider implementing rate limiting for production use

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify SUPABASE_SERVICE_ROLE_KEY is set correctly
2. **Redis Connection**: Check REDIS_URL and password configuration
3. **Email Failures**: Verify RESEND_API_KEY and domain configuration
4. **File Processing**: Ensure proper Storage bucket permissions

### Debug Mode

Enable debug logging by setting environment variable:

```bash
SUPABASE_DEBUG=true
```

## Contributing

When adding new Edge Functions:

1. Follow the established directory structure
2. Use shared utilities from `_shared/` directory
3. Include comprehensive JSDoc documentation
4. Add appropriate error handling and logging
5. Update this README with new function details
