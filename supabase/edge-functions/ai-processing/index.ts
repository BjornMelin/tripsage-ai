// AI Processing Edge Function
// Handles AI-related processing tasks triggered by webhooks

import { serve } from "https://deno.land/std@0.208.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

interface AIProcessingEvent {
  event: string
  message_id?: number
  session_id?: string
  user_id: string
  trip_id?: number
  content?: string
  timestamp: string
  metadata?: any
}

serve(async (req) => {
  try {
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

    const event: AIProcessingEvent = await req.json()
    
    console.log('Processing AI event:', event.event)

    switch (event.event) {
      case 'chat.message.process':
        await processChatMessage(supabase, event)
        break
      
      case 'memory.generate.embedding':
        await generateMemoryEmbedding(supabase, event)
        break
      
      default:
        console.log('Unhandled AI processing event:', event.event)
    }

    return new Response(
      JSON.stringify({ success: true, message: 'AI processing completed' }),
      { 
        status: 200,
        headers: { 
          ...corsHeaders,
          'Content-Type': 'application/json' 
        }
      }
    )
  } catch (error) {
    console.error('Error in AI processing:', error)
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

async function processChatMessage(supabase: any, event: AIProcessingEvent) {
  if (!event.content || !event.session_id) {
    throw new Error('Missing required fields for chat message processing')
  }

  // Extract user preferences and context from the message
  const extractedInfo = await extractUserPreferences(event.content)
  
  if (extractedInfo.preferences.length > 0 || extractedInfo.context) {
    // Store as memory
    const embedding = await generateEmbedding(event.content)
    
    await supabase.from('session_memories').insert({
      session_id: event.session_id,
      user_id: event.user_id,
      content: event.content,
      embedding: embedding,
      metadata: {
        extracted_preferences: extractedInfo.preferences,
        context_type: extractedInfo.context,
        processed_at: new Date().toISOString()
      }
    })
  }

  // If this is travel-related, update long-term memories
  if (extractedInfo.preferences.some(p => p.category === 'travel')) {
    await updateLongTermMemories(supabase, event.user_id, extractedInfo.preferences)
  }

  console.log('Chat message processed and memories updated')
}

async function generateMemoryEmbedding(supabase: any, event: AIProcessingEvent) {
  // Get memories that need embeddings
  const { data: memories } = await supabase
    .from('memories')
    .select('id, content')
    .is('embedding', null)
    .limit(10)

  if (!memories || memories.length === 0) {
    console.log('No memories need embedding generation')
    return
  }

  for (const memory of memories) {
    try {
      const embedding = await generateEmbedding(memory.content)
      
      await supabase
        .from('memories')
        .update({ 
          embedding: embedding,
          metadata: {
            embedding_generated_at: new Date().toISOString()
          }
        })
        .eq('id', memory.id)
      
      console.log('Generated embedding for memory:', memory.id)
    } catch (error) {
      console.error('Failed to generate embedding for memory:', memory.id, error)
    }
  }
}

async function extractUserPreferences(content: string): Promise<{
  preferences: Array<{ category: string; preference: string; confidence: number }>;
  context: string | null;
}> {
  // This would use an AI model to extract preferences from user messages
  // For now, return a mock implementation
  
  const preferences = []
  let context = null

  // Simple keyword-based extraction (replace with actual AI model)
  const travelKeywords = ['hotel', 'flight', 'destination', 'budget', 'vacation', 'trip']
  const budgetKeywords = ['cheap', 'expensive', 'budget', 'luxury', 'affordable']
  const accommodationKeywords = ['hotel', 'airbnb', 'resort', 'hostel']

  if (travelKeywords.some(keyword => content.toLowerCase().includes(keyword))) {
    context = 'travel_planning'
    
    if (budgetKeywords.some(keyword => content.toLowerCase().includes(keyword))) {
      preferences.push({
        category: 'travel',
        preference: 'budget_conscious',
        confidence: 0.8
      })
    }
    
    if (accommodationKeywords.some(keyword => content.toLowerCase().includes(keyword))) {
      preferences.push({
        category: 'accommodation',
        preference: 'hotel_preference',
        confidence: 0.7
      })
    }
  }

  return { preferences, context }
}

async function generateEmbedding(text: string): Promise<number[]> {
  // This would call OpenAI's embedding API or another embedding service
  // For now, return a mock embedding
  
  const openAIApiKey = Deno.env.get('OPENAI_API_KEY')
  
  if (!openAIApiKey) {
    console.warn('No OpenAI API key found, returning mock embedding')
    // Return a mock 1536-dimensional embedding
    return Array.from({ length: 1536 }, () => Math.random() * 2 - 1)
  }

  try {
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAIApiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        input: text,
        model: 'text-embedding-3-small',
        dimensions: 1536
      })
    })

    if (!response.ok) {
      throw new Error(`OpenAI API error: ${response.statusText}`)
    }

    const data = await response.json()
    return data.data[0].embedding
  } catch (error) {
    console.error('Failed to generate embedding:', error)
    // Return mock embedding on failure
    return Array.from({ length: 1536 }, () => Math.random() * 2 - 1)
  }
}

async function updateLongTermMemories(
  supabase: any,
  userId: string,
  preferences: Array<{ category: string; preference: string; confidence: number }>
) {
  for (const pref of preferences) {
    // Check if similar preference already exists
    const { data: existingMemories } = await supabase
      .from('memories')
      .select('id, content, metadata')
      .eq('user_id', userId)
      .eq('memory_type', 'user_preference')
      .ilike('content', `%${pref.preference}%`)

    if (existingMemories && existingMemories.length > 0) {
      // Update existing memory confidence
      const memory = existingMemories[0]
      await supabase
        .from('memories')
        .update({
          metadata: {
            ...memory.metadata,
            confidence: Math.max(
              memory.metadata?.confidence || 0,
              pref.confidence
            ),
            last_reinforced: new Date().toISOString()
          }
        })
        .eq('id', memory.id)
    } else {
      // Create new memory
      const embedding = await generateEmbedding(pref.preference)
      
      await supabase.from('memories').insert({
        user_id: userId,
        memory_type: 'user_preference',
        content: `User prefers ${pref.preference} in ${pref.category}`,
        embedding: embedding,
        metadata: {
          category: pref.category,
          preference: pref.preference,
          confidence: pref.confidence,
          created_at: new Date().toISOString()
        }
      })
    }
  }
}