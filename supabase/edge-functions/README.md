# TripSage Edge Functions

This directory contains Supabase Edge Functions that handle serverless processing for TripSage. Edge Functions run on Deno and are deployed globally for low-latency execution.

## 📋 Overview

Edge Functions in TripSage handle:

- AI processing and chat completions
- Real-time trip collaboration events
- Webhook processing for database changes
- Asynchronous background tasks

## 📁 Function Directory

| Function | Purpose | Triggers |
|----------|---------|----------|
| `ai-processing` | Handles AI chat completions and memory processing | HTTP requests from frontend |
| `trip-events` | Processes trip collaboration notifications | Database webhooks on `trip_collaborators` |

## 🚀 Development Setup

### Prerequisites

1. **Install Deno:**

   ```bash
   curl -fsSL https://deno.land/install.sh | sh
   ```

2. **Install Supabase CLI:**

   ```bash
   npm install -g supabase
   ```

3. **Start local Supabase:**

   ```bash
   supabase start
   ```

### Local Development

1. **Serve functions locally:**

   ```bash
   supabase functions serve
   ```

2. **Serve specific function:**

   ```bash
   supabase functions serve ai-processing --no-verify-jwt
   ```

3. **Watch for changes:**

   ```bash
   supabase functions serve --watch
   ```

## 📝 Function Structure

### Standard Function Template

```typescript
// index.ts
import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// CORS headers for browser requests
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Get auth token
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) {
      throw new Error("Missing authorization header");
    }

    // Verify user
    const token = authHeader.replace("Bearer ", "");
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    
    if (authError || !user) {
      throw new Error("Invalid authentication");
    }

    // Parse request body
    const body = await req.json();
    
    // Your function logic here
    const result = await processRequest(body, user, supabase);

    // Return response
    return new Response(
      JSON.stringify({ success: true, data: result }),
      { 
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 200 
      }
    );
  } catch (error) {
    // Error handling
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { 
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 400 
      }
    );
  }
});
```

## 🔧 Function Examples

### AI Processing Function

Handles chat completions with OpenAI integration:

```typescript
// ai-processing/index.ts
interface ChatRequest {
  messages: Message[];
  tripId?: string;
  sessionId: string;
}

async function processChat(
  request: ChatRequest,
  user: User,
  supabase: SupabaseClient
): Promise<ChatResponse> {
  // 1. Load trip context if provided
  let tripContext = "";
  if (request.tripId) {
    const { data: trip } = await supabase
      .from("trips")
      .select("*")
      .eq("id", request.tripId)
      .single();
    
    tripContext = formatTripContext(trip);
  }

  // 2. Get user memories
  const memories = await getUserMemories(user.id, supabase);

  // 3. Call OpenAI
  const completion = await openai.chat.completions.create({
    model: "gpt-4-turbo-preview",
    messages: [
      { role: "system", content: buildSystemPrompt(tripContext, memories) },
      ...request.messages
    ],
    temperature: 0.7,
    max_tokens: 1000
  });

  // 4. Save to database
  await saveChatMessage(request.sessionId, completion, supabase);

  return completion;
}
```

### Trip Events Function

Processes collaboration events and sends notifications:

```typescript
// trip-events/index.ts
interface WebhookPayload {
  type: "INSERT" | "UPDATE" | "DELETE";
  table: string;
  record: any;
  old_record?: any;
}

async function processTripEvent(
  payload: WebhookPayload,
  supabase: SupabaseClient
): Promise<void> {
  if (payload.table !== "trip_collaborators") return;

  switch (payload.type) {
    case "INSERT":
      // New collaborator added
      await notifyNewCollaborator(payload.record, supabase);
      break;
    
    case "UPDATE":
      // Permission changed
      await notifyPermissionChange(payload.record, payload.old_record, supabase);
      break;
    
    case "DELETE":
      // Collaborator removed
      await notifyCollaboratorRemoved(payload.old_record, supabase);
      break;
  }
}

async function notifyNewCollaborator(
  record: TripCollaborator,
  supabase: SupabaseClient
): Promise<void> {
  // Get trip and user details
  const { data: trip } = await supabase
    .from("trips")
    .select("name, user_id")
    .eq("id", record.trip_id)
    .single();

  const { data: invitedUser } = await supabase
    .from("auth.users")
    .select("email")
    .eq("id", record.user_id)
    .single();

  // Send email notification
  await sendEmail({
    to: invitedUser.email,
    subject: `You've been invited to collaborate on "${trip.name}"`,
    template: "trip-invitation",
    data: {
      tripName: trip.name,
      permission: record.permission_level,
      inviteUrl: `${APP_URL}/trips/${record.trip_id}`
    }
  });
}
```

## 🧪 Testing Functions

### Unit Tests

Each function includes comprehensive tests:

```typescript
// ai-processing/index.test.ts
import { assertEquals } from "https://deno.land/std/testing/asserts.ts";
import { serve } from "./index.ts";

Deno.test("AI Processing - Valid Request", async () => {
  const request = new Request("http://localhost:54321/functions/v1/ai-processing", {
    method: "POST",
    headers: {
      "Authorization": "Bearer valid_token",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      messages: [{ role: "user", content: "Plan a trip to Paris" }],
      sessionId: "test-session"
    })
  });

  const response = await serve(request);
  const data = await response.json();

  assertEquals(response.status, 200);
  assertEquals(data.success, true);
  assertExists(data.data.completion);
});
```

### Running Tests

```bash
# Run all tests
deno test --allow-all

# Run specific function tests
deno test ai-processing/index.test.ts --allow-all

# Run with coverage
deno test --allow-all --coverage=coverage
```

## 🚀 Deployment

### Deploy All Functions

```bash
supabase functions deploy
```

### Deploy Specific Function

```bash
supabase functions deploy ai-processing
supabase functions deploy trip-events
```

### Set Environment Variables

```bash
# Set secrets for functions
supabase secrets set OPENAI_API_KEY=your_openai_key
supabase secrets set RESEND_API_KEY=your_resend_key
supabase secrets set WEBHOOK_SECRET=your_webhook_secret
```

### Configure Webhooks

Set up database webhooks in Supabase Dashboard:

1. Go to Database → Webhooks
2. Create new webhook:
   - **Name**: `trip-collaborator-events`
   - **Table**: `trip_collaborators`
   - **Events**: Insert, Update, Delete
   - **URL**: `https://your-project.supabase.co/functions/v1/trip-events`
   - **Headers**:

     ```json
     {
       "Authorization": "Bearer ${SUPABASE_SERVICE_ROLE_KEY}",
       "x-webhook-secret": "${WEBHOOK_SECRET}"
     }
     ```

## 📊 Monitoring

### View Function Logs

```bash
# Real-time logs
supabase functions logs ai-processing --tail

# Historical logs
supabase functions logs trip-events --limit 100
```

### Metrics to Monitor

- **Response times**: Should be < 1s for most operations
- **Error rates**: Monitor 4xx and 5xx responses
- **Cold starts**: First invocation after idle period
- **Memory usage**: Edge Functions have 150MB limit

## 🔒 Security Best Practices

### 1. **Always Validate Auth**

```typescript
const { data: { user }, error } = await supabase.auth.getUser(token);
if (error || !user) {
  return new Response("Unauthorized", { status: 401 });
}
```

### 2. **Validate Webhook Signatures**

```typescript
const signature = req.headers.get("x-webhook-signature");
const isValid = await verifyWebhookSignature(signature, body, secret);
if (!isValid) {
  return new Response("Invalid signature", { status: 401 });
}
```

### 3. **Use Service Role Key Carefully**

```typescript
// Only use service role for admin operations
const adminSupabase = createClient(url, serviceRoleKey);

// Use user's token for user operations
const userSupabase = createClient(url, anonKey, {
  global: { headers: { Authorization: authHeader } }
});
```

### 4. **Implement Rate Limiting**

```typescript
const rateLimiter = new Map<string, number[]>();

function checkRateLimit(userId: string, limit: number = 10): boolean {
  const now = Date.now();
  const userRequests = rateLimiter.get(userId) || [];
  
  // Remove requests older than 1 minute
  const recentRequests = userRequests.filter(time => now - time < 60000);
  
  if (recentRequests.length >= limit) {
    return false;
  }
  
  recentRequests.push(now);
  rateLimiter.set(userId, recentRequests);
  return true;
}
```

## 🔧 Environment Variables

### Required for All Functions

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### Function-Specific Variables

#### AI Processing

```bash
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...
ANTHROPIC_API_KEY=sk-ant-...
```

#### Trip Events

```bash
RESEND_API_KEY=re_...
WEBHOOK_SECRET=whsec_...
APP_URL=https://your-app.com
EMAIL_FROM=notifications@your-app.com
```

## 🚨 Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure CORS headers are set in response
   - Check allowed origins match your frontend URL

2. **Authentication Failures**
   - Verify JWT token is valid
   - Check service role key is set correctly

3. **Timeout Errors**
   - Edge Functions have 150s timeout
   - Break long operations into smaller chunks

4. **Memory Errors**
   - Functions have 150MB memory limit
   - Stream large responses instead of loading in memory

### Debug Tips

```typescript
// Add debug logging
console.log("Debug:", { 
  userId: user.id,
  requestBody: body,
  timestamp: new Date().toISOString()
});

// Check environment
console.log("Environment:", {
  hasSupabaseUrl: !!Deno.env.get("SUPABASE_URL"),
  hasServiceKey: !!Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),
  denoVersion: Deno.version
});
```

## 📚 Resources

- [Supabase Edge Functions Docs](https://supabase.com/docs/guides/functions)
- [Deno Documentation](https://deno.land/manual)
- [Edge Functions Examples](https://github.com/supabase/supabase/tree/master/examples/edge-functions)
- [Deno Deploy Limitations](https://deno.com/deploy/docs/limits)

---

**Note:** Edge Functions are stateless and distributed globally. Design accordingly and use Supabase Database or Storage for persistent state.
