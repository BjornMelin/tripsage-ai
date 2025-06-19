/**
 * Trip Notification Edge Function
 * 
 * Handles trip collaboration notifications including:
 * - User added/removed notifications
 * - Permission changes
 * - Trip sharing invitations
 * - Real-time trip updates via webhooks
 * 
 * @module trip-notifications
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.1";

// Type definitions
interface WebhookPayload {
  type: 'INSERT' | 'UPDATE' | 'DELETE';
  table: string;
  record: Record<string, any>;
  old_record?: Record<string, any>;
  schema: string;
}

interface NotificationRequest {
  event_type: 'collaboration_added' | 'collaboration_removed' | 'permission_changed' | 'trip_shared';
  trip_id: number;
  user_id: string;
  target_user_id?: string;
  permission_level?: 'view' | 'edit' | 'admin';
  message?: string;
}

interface EmailPayload {
  to: string;
  subject: string;
  html: string;
  text: string;
}

// Environment variables
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY');
const NOTIFICATION_WEBHOOK_URL = Deno.env.get('NOTIFICATION_WEBHOOK_URL');

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

/**
 * Validates the incoming request and authentication
 */
async function validateRequest(req: Request): Promise<{ isValid: boolean; error?: string }> {
  try {
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
 * Fetches user details from the database
 */
async function getUserDetails(userId: string) {
  const { data, error } = await supabase
    .from('auth.users')
    .select('id, email, raw_user_meta_data')
    .eq('id', userId)
    .single();

  if (error) {
    console.error('Error fetching user details:', error);
    return null;
  }

  return {
    id: data.id,
    email: data.email,
    name: data.raw_user_meta_data?.full_name || data.email.split('@')[0]
  };
}

/**
 * Fetches trip details from the database
 */
async function getTripDetails(tripId: number) {
  const { data, error } = await supabase
    .from('trips')
    .select('id, name, destination, start_date, end_date, user_id')
    .eq('id', tripId)
    .single();

  if (error) {
    console.error('Error fetching trip details:', error);
    return null;
  }

  return data;
}

/**
 * Sends email notification using Resend API
 */
async function sendEmailNotification(payload: EmailPayload): Promise<boolean> {
  if (!RESEND_API_KEY) {
    console.warn('Resend API key not configured, skipping email notification');
    return false;
  }

  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
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

/**
 * Sends webhook notification to external service
 */
async function sendWebhookNotification(data: any): Promise<boolean> {
  if (!NOTIFICATION_WEBHOOK_URL) {
    console.log('No webhook URL configured, skipping webhook notification');
    return true;
  }

  try {
    const response = await fetch(NOTIFICATION_WEBHOOK_URL, {
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

    if (!response.ok) {
      console.error('Webhook notification failed:', response.status);
      return false;
    }

    return true;
  } catch (error) {
    console.error('Webhook error:', error);
    return false;
  }
}

/**
 * Generates email content for collaboration notifications
 */
function generateCollaborationEmail(
  event_type: NotificationRequest['event_type'],
  trip: any,
  inviter: any,
  invitee: any,
  permission_level?: string
): EmailPayload {
  const baseUrl = SUPABASE_URL.replace('.supabase.co', '.app');
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

/**
 * Handles database webhook events
 */
async function handleWebhookEvent(payload: WebhookPayload) {
  console.log('Processing webhook event:', payload.type, payload.table);

  if (payload.table === 'trip_collaborators') {
    const record = payload.record;
    const oldRecord = payload.old_record;

    // Get user details
    const [tripOwner, collaborator] = await Promise.all([
      record.added_by ? getUserDetails(record.added_by) : null,
      getUserDetails(record.user_id)
    ]);

    // Get trip details
    const trip = await getTripDetails(record.trip_id);

    if (!trip || !collaborator) {
      console.error('Missing required data for notification');
      return;
    }

    let notificationType: NotificationRequest['event_type'];
    
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
      const emailPayload = generateCollaborationEmail(
        notificationType,
        trip,
        tripOwner,
        collaborator,
        record.permission_level
      );
      
      await sendEmailNotification(emailPayload);
    }

    // Send webhook notification
    await sendWebhookNotification({
      event_type: notificationType,
      trip_id: trip.id,
      trip_name: trip.name,
      user_id: record.user_id,
      permission_level: record.permission_level,
      added_by: record.added_by
    });
  }
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
      const payload = await req.json() as WebhookPayload;
      await handleWebhookEvent(payload);
      
      return new Response(JSON.stringify({ success: true }), {
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

    // Process notification request
    const notificationReq = await req.json() as NotificationRequest;

    // Validate required fields
    if (!notificationReq.event_type || !notificationReq.trip_id || !notificationReq.user_id) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get necessary data
    const [trip, user, targetUser] = await Promise.all([
      getTripDetails(notificationReq.trip_id),
      getUserDetails(notificationReq.user_id),
      notificationReq.target_user_id ? getUserDetails(notificationReq.target_user_id) : null
    ]);

    if (!trip || !user) {
      return new Response(JSON.stringify({ error: 'Invalid trip or user' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Send notifications
    const results = await Promise.all([
      targetUser?.email ? sendEmailNotification(generateCollaborationEmail(
        notificationReq.event_type,
        trip,
        user,
        targetUser,
        notificationReq.permission_level
      )) : Promise.resolve(false),
      sendWebhookNotification({
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
});