// Trip Events Edge Function
// Handles webhook events for trip collaboration and updates

import { serve } from "https://deno.land/std@0.208.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

interface TripEvent {
  event: string
  trip_id: number
  user_id: string
  added_by?: string
  permission_level?: string
  timestamp: string
  operation: string
  data: any
}

serve(async (req) => {
  try {
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-webhook-event, x-webhook-timestamp',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
    }

    if (req.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders })
    }

    if (req.method !== 'POST') {
      return new Response('Method not allowed', { 
        status: 405, 
        headers: corsHeaders 
      })
    }

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Parse request
    const event: TripEvent = await req.json()
    
    console.log('Processing trip event:', event.event, 'for trip:', event.trip_id)

    // Handle different event types
    switch (event.event) {
      case 'trip.collaborator.added':
        await handleCollaboratorAdded(supabase, event)
        break
      
      case 'trip.collaborator.updated':
        await handleCollaboratorUpdated(supabase, event)
        break
      
      case 'trip.collaborator.removed':
        await handleCollaboratorRemoved(supabase, event)
        break
      
      default:
        console.log('Unhandled event type:', event.event)
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
    )
  } catch (error) {
    console.error('Error processing trip event:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Internal server error',
        message: error.message 
      }),
      { 
        status: 500,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    )
  }
})

async function handleCollaboratorAdded(supabase: any, event: TripEvent) {
  // Get trip details
  const { data: trip } = await supabase
    .from('trips')
    .select('name, destination, user_id')
    .eq('id', event.trip_id)
    .single()

  if (!trip) {
    throw new Error('Trip not found')
  }

  // Get user details for the new collaborator
  const { data: collaborator } = await supabase
    .from('auth.users')
    .select('email, raw_user_meta_data')
    .eq('id', event.user_id)
    .single()

  // Get trip owner details
  const { data: owner } = await supabase
    .from('auth.users')
    .select('email, raw_user_meta_data')
    .eq('id', trip.user_id)
    .single()

  // Create notification for the new collaborator
  await supabase.from('notifications').insert({
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
  })

  // Send email notification (if email service is configured)
  if (collaborator?.email) {
    await sendEmailNotification({
      to: collaborator.email,
      template: 'trip-collaboration-invite',
      data: {
        trip_name: trip.name,
        destination: trip.destination,
        owner_name: owner?.raw_user_meta_data?.full_name || owner?.email,
        permission_level: event.permission_level
      }
    })
  }

  console.log('Collaborator added notification sent for trip:', event.trip_id)
}

async function handleCollaboratorUpdated(supabase: any, event: TripEvent) {
  // Create notification for permission change
  const { data: trip } = await supabase
    .from('trips')
    .select('name, destination')
    .eq('id', event.trip_id)
    .single()

  await supabase.from('notifications').insert({
    user_id: event.user_id,
    type: 'trip_collaboration_updated',
    title: 'Trip collaboration updated',
    message: `Your permissions for "${trip.name}" have been updated to ${event.permission_level}`,
    metadata: {
      trip_id: event.trip_id,
      trip_name: trip.name,
      new_permission_level: event.permission_level
    }
  })

  console.log('Collaborator updated notification sent for trip:', event.trip_id)
}

async function handleCollaboratorRemoved(supabase: any, event: TripEvent) {
  // Create notification for removal
  const { data: trip } = await supabase
    .from('trips')
    .select('name, destination')
    .eq('id', event.trip_id)
    .single()

  await supabase.from('notifications').insert({
    user_id: event.user_id,
    type: 'trip_collaboration_removed',
    title: 'Removed from trip',
    message: `You've been removed from "${trip.name}" collaboration`,
    metadata: {
      trip_id: event.trip_id,
      trip_name: trip.name
    }
  })

  console.log('Collaborator removed notification sent for trip:', event.trip_id)
}

async function sendEmailNotification(options: {
  to: string
  template: string
  data: any
}) {
  // This would integrate with your email service (SendGrid, Resend, etc.)
  // For now, just log the notification
  console.log('Email notification would be sent:', options)
  
  // Example implementation with a hypothetical email service:
  /*
  const emailServiceUrl = Deno.env.get('EMAIL_SERVICE_URL')
  if (emailServiceUrl) {
    await fetch(emailServiceUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${Deno.env.get('EMAIL_SERVICE_API_KEY')}`
      },
      body: JSON.stringify(options)
    })
  }
  */
}