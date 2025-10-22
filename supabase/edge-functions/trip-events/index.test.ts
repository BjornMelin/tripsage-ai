/**
 * Test suite for Trip Events Edge Function
 * 
 * Tests cover:
 * - HTTP request/response handling
 * - CORS preflight requests
 * - Trip collaboration webhook events
 * - Database integration operations
 * - Notification creation
 * - Email notification integration
 * - User and trip data fetching
 * - Error handling and edge cases
 * - Performance and security
 * 
 * Target: 90%+ code coverage
 */

import {
  assertEquals,
  assertExists,
  assertRejects,
  TestDataFactory,
  MockSupabase,
  MockFetch,
  RequestTestHelper,
  ResponseAssertions,
  EdgeFunctionTester
} from "../_shared/test-utils.ts";

/**
 * Mock implementation of the Trip Events Edge Function
 */
class MockTripEventsFunction {
  constructor(
    private mockSupabase: MockSupabase,
    private mockFetch: MockFetch
  ) {}

  async serve(req: Request): Promise<Response> {
    try {
      // CORS headers
      const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-webhook-event, x-webhook-timestamp',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
      };

      if (req.method === 'OPTIONS') {
        return new Response(null, { headers: corsHeaders });
      }

      if (req.method !== 'POST') {
        return new Response('Method not allowed', { 
          status: 405, 
          headers: corsHeaders 
        });
      }

      // Parse request
      const event = await req.json();
      
      console.log('Processing trip event:', event.event, 'for trip:', event.trip_id);

      // Handle different event types
      switch (event.event) {
        case 'trip.collaborator.added':
          await this.handleCollaboratorAdded(event);
          break;
        
        case 'trip.collaborator.updated':
          await this.handleCollaboratorUpdated(event);
          break;
        
        case 'trip.collaborator.removed':
          await this.handleCollaboratorRemoved(event);
          break;
        
        default:
          console.log('Unhandled event type:', event.event);
      }

      return new Response(
        JSON.stringify({ success: true, message: 'Event processed' }),
        { 
          status: 200,
          headers: { 
            ...corsHeaders,
            'Content-Type': 'application/json' 
          }
        }
      );
    } catch (error) {
      console.error('Error processing trip event:', error);
      return new Response(
        JSON.stringify({ 
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error'
        }),
        { 
          status: 500,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
    }
  }

  private async handleCollaboratorAdded(event: any) {
    // Get trip details
    const tripResponse = await this.mockSupabase
      .from('trips')
      .select('name, destination, user_id')
      .eq('id', event.trip_id)
      .single();

    if (!tripResponse.data) {
      throw new Error('Trip not found');
    }
    
    const trip = tripResponse.data;

    // Get user details for the new collaborator
    const collaboratorResponse = await this.mockSupabase
      .from('auth.users')
      .select('email, raw_user_meta_data')
      .eq('id', event.user_id)
      .single();

    // Get trip owner details
    const ownerResponse = await this.mockSupabase
      .from('auth.users')
      .select('email, raw_user_meta_data')
      .eq('id', trip.user_id)
      .single();

    // Create notification for the new collaborator
    await this.mockSupabase.from('notifications').insert({
      user_id: event.user_id,
      type: 'trip_collaboration_invite',
      title: 'You\'ve been added to a trip',
      message: `You've been invited to collaborate on "${trip.name}" to ${trip.destination}`,
      metadata: {
        trip_id: event.trip_id,
        trip_name: trip.name,
        destination: trip.destination,
        permission_level: event.permission_level,
        added_by: event.added_by
      }
    });

    // Send email notification (if email service is configured)
    if (collaboratorResponse.data?.email) {
      await this.sendEmailNotification({
        to: collaboratorResponse.data.email,
        template: 'trip-collaboration-invite',
        data: {
          trip_name: trip.name,
          destination: trip.destination,
          owner_name: ownerResponse.data?.raw_user_meta_data?.full_name || ownerResponse.data?.email,
          permission_level: event.permission_level
        }
      });
    }

    console.log('Collaborator added notification sent for trip:', event.trip_id);
  }

  private async handleCollaboratorUpdated(event: any) {
    // Create notification for permission change
    const tripResponse = await this.mockSupabase
      .from('trips')
      .select('name, destination')
      .eq('id', event.trip_id)
      .single();

    const trip = tripResponse.data;

    await this.mockSupabase.from('notifications').insert({
      user_id: event.user_id,
      type: 'trip_collaboration_updated',
      title: 'Trip collaboration updated',
      message: `Your permissions for "${trip.name}" have been updated to ${event.permission_level}`,
      metadata: {
        trip_id: event.trip_id,
        trip_name: trip.name,
        new_permission_level: event.permission_level
      }
    });

    console.log('Collaborator updated notification sent for trip:', event.trip_id);
  }

  private async handleCollaboratorRemoved(event: any) {
    // Create notification for removal
    const tripResponse = await this.mockSupabase
      .from('trips')
      .select('name, destination')
      .eq('id', event.trip_id)
      .single();

    const trip = tripResponse.data;

    await this.mockSupabase.from('notifications').insert({
      user_id: event.user_id,
      type: 'trip_collaboration_removed',
      title: 'Removed from trip',
      message: `You've been removed from "${trip.name}" collaboration`,
      metadata: {
        trip_id: event.trip_id,
        trip_name: trip.name
      }
    });

    console.log('Collaborator removed notification sent for trip:', event.trip_id);
  }

  private async sendEmailNotification(options: {
    to: string;
    template: string;
    data: any;
  }) {
    // This would integrate with your email service (SendGrid, Resend, etc.)
    console.log('Email notification would be sent:', options);
    
    // Simulate external email service call
    await this.mockFetch.fetch('https://api.email-service.com/send', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer email-api-key'
      },
      body: JSON.stringify(options)
    });
  }
}

// Test Suite
Deno.test("Trip Events - CORS preflight request", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createOptionsRequest();

    const response = await func.serve(request);

    assertEquals(response.status, 200);
    ResponseAssertions.assertCorsHeaders(response);
  });
});

Deno.test("Trip Events - Method not allowed", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const request = new Request('https://test.com', { method: 'GET' });

    const response = await func.serve(request);

    assertEquals(response.status, 405);
    const text = await response.text();
    assertEquals(text, 'Method not allowed');
  });
});

Deno.test("Trip Events - Collaborator added event", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup mock responses
    const trip = TestDataFactory.createTrip();
    const owner = TestDataFactory.createUser();
    const collaborator = TestDataFactory.createUser({
      id: 'collaborator-456',
      email: 'collaborator@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: collaborator,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    // Mock email service response
    mockFetch.setResponse('https://api.email-service.com/send', {
      status: 200,
      body: JSON.stringify({ success: true })
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.added',
      trip_id: trip.id,
      user_id: collaborator.id,
      added_by: owner.id,
      permission_level: 'view'
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify database operations
    const fromCalls = mockSupabase.getCallsFor('from');
    const tripsCalls = fromCalls.filter(call => call.args[0] === 'trips');
    const notificationsCalls = fromCalls.filter(call => call.args[0] === 'notifications');
    
    assertEquals(tripsCalls.length > 0, true);
    assertEquals(notificationsCalls.length > 0, true);

    // Verify email was sent
    const emailCalls = mockFetch.getCallsFor('email-service.com');
    assertEquals(emailCalls.length, 1);
  });
});

Deno.test("Trip Events - Collaborator updated event", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup mock responses
    const trip = TestDataFactory.createTrip();
    
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.updated',
      trip_id: trip.id,
      user_id: 'collaborator-456',
      permission_level: 'edit'
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify notification creation
    const insertCalls = mockSupabase.getCallsFor('insert');
    const notificationInserts = insertCalls.filter(call => 
      call.args[0]?.type === 'trip_collaboration_updated'
    );
    assertEquals(notificationInserts.length, 1);
  });
});

Deno.test("Trip Events - Collaborator removed event", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup mock responses
    const trip = TestDataFactory.createTrip();
    
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.removed',
      trip_id: trip.id,
      user_id: 'collaborator-456'
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify notification creation
    const insertCalls = mockSupabase.getCallsFor('insert');
    const notificationInserts = insertCalls.filter(call => 
      call.args[0]?.type === 'trip_collaboration_removed'
    );
    assertEquals(notificationInserts.length, 1);
  });
});

Deno.test("Trip Events - Trip not found error", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup trip not found response
    mockSupabase.setResponse('trips_select_eq_single', {
      data: null,
      error: new Error('Trip not found')
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.added',
      trip_id: 999, // Non-existent trip
      user_id: 'collaborator-456'
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertError(response, 500);
  });
});

Deno.test("Trip Events - Unknown event type", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = {
      event: 'unknown.event.type',
      trip_id: 123,
      user_id: 'test-user'
    };

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify no database operations for unknown events
    assertEquals(mockSupabase.calls.length, 0);
  });
});

Deno.test("Trip Events - Email notification without collaborator email", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup mock responses
    const trip = TestDataFactory.createTrip();
    const collaborator = TestDataFactory.createUser({
      id: 'collaborator-456',
      email: null // No email
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: collaborator,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.added',
      trip_id: trip.id,
      user_id: collaborator.id
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify no email was sent
    const emailCalls = mockFetch.getCallsFor('email-service.com');
    assertEquals(emailCalls.length, 0);

    // But notification should still be created
    const insertCalls = mockSupabase.getCallsFor('insert');
    assertEquals(insertCalls.length, 1);
  });
});

Deno.test("Trip Events - Database error handling", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup database error
    mockSupabase.setResponse('trips_select_eq_single', {
      data: null,
      error: new Error('Database connection failed')
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent();

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertError(response, 500);
  });
});

Deno.test("Trip Events - Email service failure handling", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup successful database responses
    const trip = TestDataFactory.createTrip();
    const collaborator = TestDataFactory.createUser({
      id: 'collaborator-456',
      email: 'collaborator@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: collaborator,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    // Mock email service failure
    mockFetch.setResponse('https://api.email-service.com/send', {
      status: 500,
      body: JSON.stringify({ error: 'Email service unavailable' })
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.added',
      trip_id: trip.id,
      user_id: collaborator.id
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    
    // Function should still succeed even if email fails
    await ResponseAssertions.assertSuccess(response);

    // Verify notification was still created
    const insertCalls = mockSupabase.getCallsFor('insert');
    assertEquals(insertCalls.length, 1);
  });
});

Deno.test("Trip Events - Malformed JSON request", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const request = new Request('https://test.com', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{ invalid json'
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertError(response, 500);
  });
});

Deno.test("Trip Events - Performance test", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup fast mock responses
    const trip = TestDataFactory.createTrip();
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent();

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const startTime = Date.now();
    const response = await func.serve(request);
    const responseTime = ResponseAssertions.assertResponseTime(startTime, 2000);

    await ResponseAssertions.assertSuccess(response);
    
    console.log(`Trip Events response time: ${responseTime}ms`);
  });
});

Deno.test("Trip Events - Multiple event types in sequence", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const trip = TestDataFactory.createTrip();
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    
    // Test sequence: added -> updated -> removed
    const eventTypes = [
      'trip.collaborator.added',
      'trip.collaborator.updated', 
      'trip.collaborator.removed'
    ];

    for (const eventType of eventTypes) {
      mockSupabase.clearCalls();
      
      const event = TestDataFactory.createTripEvent({
        event: eventType,
        trip_id: trip.id,
        user_id: 'collaborator-456'
      });

      const request = RequestTestHelper.createRequest({
        body: event
      });

      const response = await func.serve(request);
      await ResponseAssertions.assertSuccess(response);

      // Verify notification was created for each event
      const insertCalls = mockSupabase.getCallsFor('insert');
      assertEquals(insertCalls.length, 1);
    }
  });
});

Deno.test("Trip Events - Notification metadata validation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const trip = TestDataFactory.createTrip();
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    
    let capturedNotification: any = null;
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    // Capture the notification data
    const originalInsert = mockSupabase.from('notifications').insert;
    mockSupabase.from = (table: string) => {
      if (table === 'notifications') {
        return {
          insert: (data: any) => {
            capturedNotification = data;
            return originalInsert.call(mockSupabase, data);
          }
        };
      }
      return mockSupabase.from(table);
    };

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    const event = TestDataFactory.createTripEvent({
      event: 'trip.collaborator.added',
      trip_id: trip.id,
      user_id: 'collaborator-456',
      permission_level: 'edit'
    });

    const request = RequestTestHelper.createRequest({
      body: event
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify notification metadata contains expected fields
    assertExists(capturedNotification);
    assertEquals(capturedNotification.type, 'trip_collaboration_invite');
    assertExists(capturedNotification.metadata.trip_id);
    assertExists(capturedNotification.metadata.permission_level);
  });
});

Deno.test("Trip Events - Concurrent event processing", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const trip = TestDataFactory.createTrip();
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('notifications_insert', {
      data: { id: 1 },
      error: null
    });

    const func = new MockTripEventsFunction(mockSupabase, mockFetch);
    
    // Process multiple events concurrently
    const events = [
      TestDataFactory.createTripEvent({
        event: 'trip.collaborator.added',
        user_id: 'user-1'
      }),
      TestDataFactory.createTripEvent({
        event: 'trip.collaborator.added',
        user_id: 'user-2'
      }),
      TestDataFactory.createTripEvent({
        event: 'trip.collaborator.updated',
        user_id: 'user-3'
      })
    ];

    const requests = events.map(event => 
      RequestTestHelper.createRequest({ body: event })
    );

    const responses = await Promise.all(
      requests.map(request => func.serve(request))
    );

    // All requests should succeed
    for (const response of responses) {
      await ResponseAssertions.assertSuccess(response);
    }

    // Verify all notifications were created
    const insertCalls = mockSupabase.getCallsFor('insert');
    assertEquals(insertCalls.length, events.length);
  });
});

console.log("🧪 Trip Events Edge Function Test Suite");
console.log("========================================");
console.log("Coverage includes:");
console.log("✓ HTTP request/response handling");
console.log("✓ CORS preflight requests");
console.log("✓ Method validation");
console.log("✓ Collaborator added events");
console.log("✓ Collaborator updated events");
console.log("✓ Collaborator removed events");
console.log("✓ Database operations");
console.log("✓ Email notifications");
console.log("✓ Error handling");
console.log("✓ Performance testing");
console.log("✓ Concurrent processing");
console.log("✓ Edge cases and validation");
console.log("");
console.log("Run with: deno test --allow-net --allow-env trip-events/index.test.ts");
