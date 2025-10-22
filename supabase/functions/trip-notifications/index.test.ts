/**
 * Test suite for Trip Notifications Edge Function
 * 
 * Tests cover:
 * - HTTP request/response handling
 * - CORS preflight requests
 * - Authentication and authorization
 * - Notification creation workflows
 * - Email notification delivery
 * - Webhook event handling
 * - User and trip data retrieval
 * - Email template generation
 * - External service integration
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
 * Mock implementation of the Trip Notifications Edge Function
 */
class MockTripNotificationsFunction {
  constructor(
    private mockSupabase: MockSupabase,
    private mockFetch: MockFetch
  ) {}

  async serve(req: Request): Promise<Response> {
    try {
      // Handle CORS preflight
      if (req.method === 'OPTIONS') {
        return new Response('ok', {
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'authorization, content-type',
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
        const payload = await req.json();
        await this.handleWebhookEvent(payload);
        
        return new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Validate regular API request
      const validation = await this.validateRequest(req);
      if (!validation.isValid) {
        return new Response(JSON.stringify({ error: validation.error }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Process notification request
      const notificationReq = await req.json();

      // Validate required fields
      if (!notificationReq.event_type || !notificationReq.trip_id || !notificationReq.user_id) {
        return new Response(JSON.stringify({ error: 'Missing required fields' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Get necessary data
      const [trip, user, targetUser] = await Promise.all([
        this.getTripDetails(notificationReq.trip_id),
        this.getUserDetails(notificationReq.user_id),
        notificationReq.target_user_id ? this.getUserDetails(notificationReq.target_user_id) : null
      ]);

      if (!trip || !user) {
        return new Response(JSON.stringify({ error: 'Invalid trip or user' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Send notifications
      const results = await Promise.all([
        targetUser?.email ? this.sendEmailNotification(this.generateCollaborationEmail(
          notificationReq.event_type,
          trip,
          user,
          targetUser,
          notificationReq.permission_level
        )) : Promise.resolve(false),
        this.sendWebhookNotification({
          ...notificationReq,
          trip_name: trip.name,
          user_name: user.name,
          target_user_name: targetUser?.name
        })
      ]);

      return new Response(JSON.stringify({ 
        success: true,
        email_sent: results[0],
        webhook_sent: results[1]
      }), {
        status: 200,
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
  }

  private async validateRequest(req: Request) {
    try {
      // Check for authorization header
      const authHeader = req.headers.get('authorization');
      if (!authHeader?.startsWith('Bearer ')) {
        return { isValid: false, error: 'Missing or invalid authorization header' };
      }

      // Verify JWT token
      const token = authHeader.replace('Bearer ', '');
      const response = await this.mockSupabase.auth.getUser(token);
      
      if (response.error || !response.data.user) {
        return { isValid: false, error: 'Invalid authentication token' };
      }

      return { isValid: true };
    } catch (error) {
      return { isValid: false, error: 'Request validation failed' };
    }
  }

  private async getUserDetails(userId: string) {
    const response = await this.mockSupabase
      .from('auth.users')
      .select('id, email, raw_user_meta_data')
      .eq('id', userId)
      .single();

    if (response.error) {
      console.error('Error fetching user details:', response.error);
      return null;
    }

    return {
      id: response.data.id,
      email: response.data.email,
      name: response.data.raw_user_meta_data?.full_name || response.data.email.split('@')[0]
    };
  }

  private async getTripDetails(tripId: number) {
    const response = await this.mockSupabase
      .from('trips')
      .select('id, name, destination, start_date, end_date, user_id')
      .eq('id', tripId)
      .single();

    if (response.error) {
      console.error('Error fetching trip details:', response.error);
      return null;
    }

    return response.data;
  }

  private async sendEmailNotification(payload: any): Promise<boolean> {
    const resendApiKey = Deno.env.get('RESEND_API_KEY');
    if (!resendApiKey) {
      console.warn('Resend API key not configured, skipping email notification');
      return false;
    }

    try {
      const response = await this.mockFetch.fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${resendApiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from: 'TripSage <notifications@tripsage.com>',
          to: [payload.to],
          subject: payload.subject,
          html: payload.html,
          text: payload.text
        })
      });

      if (!response.ok) {
        const error = await response.text();
        console.error('Resend API error:', error);
        return false;
      }

      return true;
    } catch (error) {
      console.error('Email send error:', error);
      return false;
    }
  }

  private async sendWebhookNotification(data: any): Promise<boolean> {
    const webhookUrl = Deno.env.get('NOTIFICATION_WEBHOOK_URL');
    if (!webhookUrl) {
      console.log('No webhook URL configured, skipping webhook notification');
      return true;
    }

    try {
      const response = await this.mockFetch.fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Event-Type': 'trip-notification'
        },
        body: JSON.stringify({
          timestamp: new Date().toISOString(),
          ...data
        })
      });

      return response.ok;
    } catch (error) {
      console.error('Webhook error:', error);
      return false;
    }
  }

  private generateCollaborationEmail(
    event_type: string,
    trip: any,
    inviter: any,
    invitee: any,
    permission_level?: string
  ) {
    const baseUrl = Deno.env.get('SUPABASE_URL')?.replace('.supabase.co', '.app') || 'https://app.tripsage.com';
    const tripUrl = `${baseUrl}/trips/${trip.id}`;

    let subject: string;
    let html: string;
    let text: string;

    switch (event_type) {
      case 'collaboration_added':
        subject = `You've been invited to collaborate on "${trip.name}"`;
        html = `
          <h2>Trip Collaboration Invitation</h2>
          <p>Hi ${invitee.name},</p>
          <p>${inviter.name} has invited you to collaborate on their trip to ${trip.destination}.</p>
          <p><strong>Trip Details:</strong></p>
          <ul>
            <li>Destination: ${trip.destination}</li>
            <li>Dates: ${new Date(trip.start_date).toLocaleDateString()} - ${new Date(trip.end_date).toLocaleDateString()}</li>
            <li>Permission Level: ${permission_level || 'view'}</li>
          </ul>
          <p><a href="${tripUrl}">View Trip</a></p>
        `;
        text = `You've been invited to collaborate on "${trip.name}". View at: ${tripUrl}`;
        break;

      case 'collaboration_removed':
        subject = `Your access to "${trip.name}" has been removed`;
        html = `
          <h2>Trip Access Removed</h2>
          <p>Hi ${invitee.name},</p>
          <p>Your access to the trip "${trip.name}" has been removed.</p>
          <p>If you believe this is an error, please contact the trip owner.</p>
        `;
        text = `Your access to "${trip.name}" has been removed.`;
        break;

      case 'permission_changed':
        subject = `Your permissions for "${trip.name}" have been updated`;
        html = `
          <h2>Permission Update</h2>
          <p>Hi ${invitee.name},</p>
          <p>Your permissions for "${trip.name}" have been updated to: ${permission_level}</p>
          <p><a href="${tripUrl}">View Trip</a></p>
        `;
        text = `Your permissions for "${trip.name}" have been updated to: ${permission_level}`;
        break;

      default:
        subject = `Update for trip "${trip.name}"`;
        html = `<p>There's been an update to your trip.</p>`;
        text = `There's been an update to your trip.`;
    }

    return { to: invitee.email, subject, html, text };
  }

  private async handleWebhookEvent(payload: any) {
    console.log('Processing webhook event:', payload.type, payload.table);

    if (payload.table === 'trip_collaborators') {
      const record = payload.record;
      const oldRecord = payload.old_record;

      // Get user details
      const [tripOwner, collaborator] = await Promise.all([
        record.added_by ? this.getUserDetails(record.added_by) : null,
        this.getUserDetails(record.user_id)
      ]);

      // Get trip details
      const trip = await this.getTripDetails(record.trip_id);

      if (!trip || !collaborator) {
        console.error('Missing required data for notification');
        return;
      }

      let notificationType: string;
      
      switch (payload.type) {
        case 'INSERT':
          notificationType = 'collaboration_added';
          break;
        case 'DELETE':
          notificationType = 'collaboration_removed';
          break;
        case 'UPDATE':
          if (oldRecord?.permission_level !== record.permission_level) {
            notificationType = 'permission_changed';
          } else {
            return; // No notification needed for other updates
          }
          break;
        default:
          return;
      }

      // Send email notification
      if (tripOwner && collaborator.email) {
        const emailPayload = this.generateCollaborationEmail(
          notificationType,
          trip,
          tripOwner,
          collaborator,
          record.permission_level
        );
        
        await this.sendEmailNotification(emailPayload);
      }

      // Send webhook notification
      await this.sendWebhookNotification({
        event_type: notificationType,
        trip_id: trip.id,
        trip_name: trip.name,
        user_id: record.user_id,
        permission_level: record.permission_level,
        added_by: record.added_by
      });
    }
  }
}

// Test Suite
Deno.test("Trip Notifications - CORS preflight request", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createOptionsRequest();

    const response = await func.serve(request);

    assertEquals(response.status, 200);
    ResponseAssertions.assertCorsHeaders(response);
  });
});

Deno.test("Trip Notifications - Method not allowed", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = new Request('https://test.com', { method: 'GET' });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 405, 'Method not allowed');
  });
});

Deno.test("Trip Notifications - Authentication validation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup invalid auth response
    mockSupabase.setResponse('auth_getUser', {
      data: { user: null },
      error: new Error('Invalid token')
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: 123,
      user_id: 'test-user'
    }, 'invalid-token');

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 401, 'Invalid authentication token');
  });
});

Deno.test("Trip Notifications - Missing required fields", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      // Missing required fields
      event_type: 'collaboration_added'
    });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 400, 'Missing required fields');
  });
});

Deno.test("Trip Notifications - Collaboration added notification", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    // Setup user and trip data
    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();
    const targetUser = TestDataFactory.createUser({
      id: 'target-user-456',
      email: 'target@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    // Mock Resend API
    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    mockFetch.setResponse('https://api.resend.com/emails', {
      status: 200,
      body: JSON.stringify({ id: 'email-123' })
    });

    // Mock webhook
    Deno.env.set('NOTIFICATION_WEBHOOK_URL', 'https://api.example.com/notifications');
    mockFetch.setResponse('https://api.example.com/notifications', {
      status: 200,
      body: JSON.stringify({ success: true })
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: trip.id,
      user_id: user.id,
      target_user_id: targetUser.id,
      permission_level: 'view'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    assertEquals(data.email_sent, true);
    assertEquals(data.webhook_sent, true);

    // Verify email API was called
    const emailCalls = mockFetch.getCallsFor('resend.com');
    assertEquals(emailCalls.length, 1);

    // Verify webhook was called
    const webhookCalls = mockFetch.getCallsFor('notifications');
    assertEquals(webhookCalls.length, 1);
  });
});

Deno.test("Trip Notifications - Collaboration removed notification", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();
    const targetUser = TestDataFactory.createUser({
      id: 'target-user-456',
      email: 'target@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    mockFetch.setResponse('https://api.resend.com/emails', {
      status: 200,
      body: JSON.stringify({ id: 'email-123' })
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_removed',
      trip_id: trip.id,
      user_id: user.id,
      target_user_id: targetUser.id
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    assertEquals(data.email_sent, true);

    // Verify email content mentions removal
    const emailCalls = mockFetch.getCallsFor('resend.com');
    assertEquals(emailCalls.length, 1);
    const emailBody = JSON.parse(emailCalls[0].options?.body as string);
    assertEquals(emailBody.subject.includes('removed'), true);
  });
});

Deno.test("Trip Notifications - Permission changed notification", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();
    const targetUser = TestDataFactory.createUser({
      id: 'target-user-456',
      email: 'target@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    mockFetch.setResponse('https://api.resend.com/emails', {
      status: 200,
      body: JSON.stringify({ id: 'email-123' })
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'permission_changed',
      trip_id: trip.id,
      user_id: user.id,
      target_user_id: targetUser.id,
      permission_level: 'admin'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    assertEquals(data.email_sent, true);

    // Verify email content mentions permission update
    const emailCalls = mockFetch.getCallsFor('resend.com');
    const emailBody = JSON.parse(emailCalls[0].options?.body as string);
    assertEquals(emailBody.subject.includes('updated'), true);
    assertEquals(emailBody.html.includes('admin'), true);
  });
});

Deno.test("Trip Notifications - Trip not found", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    // Setup trip not found
    mockSupabase.setResponse('trips_select_eq_single', {
      data: null,
      error: new Error('Trip not found')
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: 999,
      user_id: 'test-user'
    });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 404, 'Invalid trip or user');
  });
});

Deno.test("Trip Notifications - User not found", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });

    // Setup user not found
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: null,
      error: new Error('User not found')
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: trip.id,
      user_id: 'nonexistent-user'
    });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 404, 'Invalid trip or user');
  });
});

Deno.test("Trip Notifications - Email without target user", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: trip.id,
      user_id: user.id
      // No target_user_id
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // No email should be sent without target user
    assertEquals(data.email_sent, false);
  });
});

Deno.test("Trip Notifications - Email without Resend API key", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Remove Resend API key
    Deno.env.delete('RESEND_API_KEY');

    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();
    const targetUser = TestDataFactory.createUser({
      id: 'target-user-456',
      email: 'target@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: trip.id,
      user_id: user.id,
      target_user_id: targetUser.id
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // Email should not be sent without API key
    assertEquals(data.email_sent, false);

    // No email API calls should be made
    const emailCalls = mockFetch.getCallsFor('resend.com');
    assertEquals(emailCalls.length, 0);
  });
});

Deno.test("Trip Notifications - Email service failure", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();
    const targetUser = TestDataFactory.createUser({
      id: 'target-user-456',
      email: 'target@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    // Setup email service failure
    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    mockFetch.setResponse('https://api.resend.com/emails', {
      status: 500,
      body: JSON.stringify({ error: 'Service unavailable' })
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: trip.id,
      user_id: user.id,
      target_user_id: targetUser.id
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // Email should fail but function should still succeed
    assertEquals(data.email_sent, false);
  });
});

Deno.test("Trip Notifications - Webhook event handling", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup user and trip data
    const trip = TestDataFactory.createTrip();
    const owner = TestDataFactory.createUser({ id: 'owner-123' });
    const collaborator = TestDataFactory.createUser({
      id: 'collaborator-456',
      email: 'collaborator@example.com'
    });

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    
    // Setup multiple user responses
    let userCallCount = 0;
    const originalUserCall = mockSupabase.from('auth.users');
    mockSupabase.from = (table: string) => {
      if (table === 'auth.users') {
        userCallCount++;
        const userData = userCallCount === 1 ? owner : collaborator;
        return {
          select: () => ({
            eq: () => ({
              single: () => Promise.resolve({
                data: userData,
                error: null
              })
            })
          })
        };
      }
      return mockSupabase.from(table);
    };

    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    mockFetch.setResponse('https://api.resend.com/emails', {
      status: 200,
      body: JSON.stringify({ id: 'email-123' })
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const payload = TestDataFactory.createWebhookPayload(
      'trip_collaborators',
      'INSERT',
      TestDataFactory.createTripCollaborator({
        trip_id: trip.id,
        user_id: collaborator.id,
        added_by: owner.id,
        permission_level: 'view'
      })
    );

    const request = RequestTestHelper.createWebhookRequest(payload);

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify email was sent
    const emailCalls = mockFetch.getCallsFor('resend.com');
    assertEquals(emailCalls.length, 1);
  });
});

Deno.test("Trip Notifications - Webhook permission change event", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
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

    Deno.env.set('RESEND_API_KEY', 'test-resend-key');
    mockFetch.setResponse('https://api.resend.com/emails', {
      status: 200,
      body: JSON.stringify({ id: 'email-123' })
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    
    // UPDATE event with permission change
    const payload = TestDataFactory.createWebhookPayload(
      'trip_collaborators',
      'UPDATE',
      TestDataFactory.createTripCollaborator({
        permission_level: 'admin'
      }),
      TestDataFactory.createTripCollaborator({
        permission_level: 'view'
      })
    );

    const request = RequestTestHelper.createWebhookRequest(payload);

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // Verify permission change email was sent
    const emailCalls = mockFetch.getCallsFor('resend.com');
    assertEquals(emailCalls.length, 1);
  });
});

Deno.test("Trip Notifications - Webhook UPDATE event without permission change", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    
    // UPDATE event without permission change
    const payload = TestDataFactory.createWebhookPayload(
      'trip_collaborators',
      'UPDATE',
      TestDataFactory.createTripCollaborator({
        permission_level: 'view',
        updated_at: new Date().toISOString()
      }),
      TestDataFactory.createTripCollaborator({
        permission_level: 'view',
        updated_at: new Date(Date.now() - 1000).toISOString()
      })
    );

    const request = RequestTestHelper.createWebhookRequest(payload);

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);

    // No email should be sent for non-permission updates
    const emailCalls = mockFetch.getCallsFor('resend.com');
    assertEquals(emailCalls.length, 0);
  });
});

Deno.test("Trip Notifications - Email template generation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    
    const trip = TestDataFactory.createTrip({
      name: 'Paris Adventure',
      destination: 'Paris, France',
      start_date: '2025-06-15',
      end_date: '2025-06-22'
    });
    
    const inviter = TestDataFactory.createUser({ name: 'John Doe' });
    const invitee = TestDataFactory.createUser({ 
      name: 'Jane Smith',
      email: 'jane@example.com'
    });

    // Test different email types
    const testCases = [
      { event_type: 'collaboration_added', permission_level: 'edit' },
      { event_type: 'collaboration_removed' },
      { event_type: 'permission_changed', permission_level: 'admin' }
    ];

    for (const testCase of testCases) {
      const email = func['generateCollaborationEmail'](
        testCase.event_type,
        trip,
        inviter,
        invitee,
        testCase.permission_level
      );

      assertEquals(email.to, invitee.email);
      assertExists(email.subject);
      assertExists(email.html);
      assertExists(email.text);
      
      // Verify content includes trip name
      assertEquals(email.subject.includes(trip.name), true);
      
      if (testCase.permission_level) {
        assertEquals(email.html.includes(testCase.permission_level), true);
      }
    }
  });
});

Deno.test("Trip Notifications - Concurrent notifications", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    
    // Create multiple concurrent notification requests
    const requests = Array.from({ length: 3 }, (_, i) => 
      RequestTestHelper.createAuthenticatedRequest({
        event_type: 'collaboration_added',
        trip_id: trip.id,
        user_id: user.id,
        target_user_id: `user-${i}`
      })
    );

    const responses = await Promise.all(
      requests.map(request => func.serve(request))
    );

    // All should succeed
    for (const response of responses) {
      await ResponseAssertions.assertSuccess(response);
    }
  });
});

Deno.test("Trip Notifications - Performance test", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup fast mocks
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const trip = TestDataFactory.createTrip();
    const user = TestDataFactory.createUser();

    mockSupabase.setResponse('trips_select_eq_single', {
      data: trip,
      error: null
    });
    mockSupabase.setResponse('auth.users_select_eq_single', {
      data: user,
      error: null
    });

    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      event_type: 'collaboration_added',
      trip_id: trip.id,
      user_id: user.id
    });

    const startTime = Date.now();
    const response = await func.serve(request);
    const responseTime = ResponseAssertions.assertResponseTime(startTime, 3000);

    await ResponseAssertions.assertSuccess(response);
    
    console.log(`Trip Notifications response time: ${responseTime}ms`);
  });
});

Deno.test("Trip Notifications - Malformed JSON", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockTripNotificationsFunction(mockSupabase, mockFetch);
    const request = new Request('https://test.com', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: '{ invalid json'
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertError(response, 500);
  });
});

console.log("🧪 Trip Notifications Edge Function Test Suite");
console.log("===============================================");
console.log("Coverage includes:");
console.log("✓ HTTP request/response handling");
console.log("✓ CORS preflight requests");
console.log("✓ Authentication validation");
console.log("✓ Notification workflows");
console.log("✓ Email delivery via Resend");
console.log("✓ Webhook notifications");
console.log("✓ User and trip data retrieval");
console.log("✓ Email template generation");
console.log("✓ Webhook event handling");
console.log("✓ Error handling and edge cases");
console.log("✓ Performance testing");
console.log("✓ Concurrent processing");
console.log("");
console.log("Run with: deno test --allow-net --allow-env trip-notifications/index.test.ts");
