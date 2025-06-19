/**
 * Shared Supabase utilities for Edge Functions
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.1";

// Environment variables
export const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
export const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
export const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!;

// Create service role client (for privileged operations)
export const supabaseAdmin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Create client with user context
export function createUserClient(authToken: string) {
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    },
  });
}

/**
 * Validates JWT token and returns user
 */
export async function validateAuth(authToken: string) {
  try {
    const { data: { user }, error } = await supabaseAdmin.auth.getUser(authToken);
    
    if (error || !user) {
      return { isValid: false, error: 'Invalid authentication token', user: null };
    }

    return { isValid: true, error: null, user };
  } catch (error) {
    return { 
      isValid: false, 
      error: error instanceof Error ? error.message : 'Authentication failed',
      user: null 
    };
  }
}