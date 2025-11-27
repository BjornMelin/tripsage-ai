# Route Exceptions

Exception criteria for bypassing the withApiGuards factory pattern.

## Overview

Most API routes should use the `withApiGuards` factory for consistent
authentication, rate limiting, error handling, and telemetry. Some routes
need custom handling that the factory cannot support.

## Exception Criteria

### 1. Webhook Receivers (`/api/hooks/*`)

**Justification**: Webhooks require signature verification before any
processing.

**Example**: Supabase webhooks with HMAC verification

```typescript
import { errorResponse } from "@/lib/api/route-helpers";

// Cannot use factory - signature verification happens first
export async function POST(req: NextRequest) {
  const signature = req.headers.get('x-webhook-signature');
  if (!signature) {
    return errorResponse({
      error: "unauthorized",
      reason: "Missing webhook signature",
      status: 401,
    });
  }

  // Verify signature before any other processing
  const body = await req.text();
  const isValid = verifyWebhookSignature(body, signature);
  if (!isValid) {
    return errorResponse({
      error: "unauthorized",
      reason: "Invalid webhook signature",
      status: 401,
    });
  }

  // Now process the webhook
  const payload = JSON.parse(body);
  await processWebhook(payload);
  return Response.json({ ok: true });
}
```

**Routes Affected**:

- `/api/hooks/cache` - Supabase cache invalidation
- `/api/hooks/files` - File processing webhooks
- `/api/hooks/trips` - Trip collaboration sync

### 2. Background Jobs (`/api/jobs/*`)

**Justification**: Background jobs have different authentication and
execution patterns.

**Example**: QStash job processing

```typescript
import { errorResponse } from "@/lib/api/route-helpers";

// Cannot use factory - custom signature verification
export async function POST(req: NextRequest) {
  const signature = req.headers.get('x-qstash-signature');
  if (!signature) {
    return errorResponse({
      error: "unauthorized",
      reason: "Missing QStash signature",
      status: 401,
    });
  }

  // Verify QStash signature
  const body = await req.text();
  const isValid = verifyQstashSignature(body, signature);
  if (!isValid) {
    return errorResponse({
      error: "unauthorized",
      reason: "Invalid QStash signature",
      status: 401,
    });
  }

  // Process job without user context
  const job = JSON.parse(body);
  await processJob(job);
  return Response.json({ ok: true });
}
```

**Routes Affected**:

- `/api/jobs/memory-sync` - User memory synchronization

### 3. Complex Custom Requirements

**Justification**: Routes with requirements the factory cannot support.

**Criteria for Approval**:

- Factory enhancement attempted first
- Document why the factory cannot support the pattern
- Team approval required before implementation
- Exception must be documented and justified

## Process for New Exceptions

### Step 1: Attempt Factory Use

Try to implement the route using `withApiGuards` first.

### Step 2: Document Limitations

If the factory cannot support requirements, document:

- What requirement cannot be met
- Why the factory cannot be enhanced
- Alternative approaches considered

### Step 3: Get Approval

- Create an ADR documenting the exception
- Get team approval for the exception
- Consider factory enhancement for future use

### Step 4: Implement and Document

- Implement the route with custom handling
- Add it to this exceptions document
- Update route lists and metrics

## Current Exceptions

| Route | Category | Justification | ADR |
|-------|----------|---------------|-----|
| `/api/hooks/cache` | Webhook | Supabase HMAC verification | ADR-0032 |
| `/api/hooks/files` | Webhook | File processing signature | ADR-0032 |
| `/api/hooks/trips` | Webhook | Trip sync signature | ADR-0032 |
| `/api/jobs/memory-sync` | Background Job | QStash signature check | ADR-0032 |

## Exception Monitoring

### Monthly Review

> **Note**: This is a reusable monthly review template. Copy and complete for each review cycle.

- [ ] Verify exceptions are still justified
- [ ] Check if the factory can support the requirements
- [ ] Review for pattern consistency
- [ ] Update documentation as needed

### Factory Enhancement

When exceptions are identified:

- [ ] Assess if the factory can be enhanced
- [ ] Implement enhancement if feasible
- [ ] Migrate exception routes to the factory
- [ ] Remove from the exceptions list

## Security Considerations

### Exception Routes Must

- [ ] Implement authentication or authorization appropriate to their use case
- [ ] Include rate limiting where applicable
- [ ] Handle errors consistently
- [ ] Include telemetry for monitoring
- [ ] Follow security best practices

### Documentation Requirements

- [ ] Security approach clearly documented
- [ ] Exception justification reviewed annually
- [ ] Alternative approaches considered
- [ ] Migration plan for future factory adoption

## Migration Strategy

### Phase 1: Identification

- Audit all routes for factory compatibility
- Document exceptions with justification
- Establish a monitoring process

### Phase 2: Enhancement

- Identify common exception patterns
- Enhance the factory to support those patterns
- Update the factory with new capabilities

### Phase 3: Migration

- Migrate eligible exception routes to the enhanced factory
- Update exception documentation
- Monitor for issues

### Phase 4: Consolidation

- Minimize exceptions over time
- Maintain high factory adoption
- Document lessons learned

## Metrics

| Metric | Current |
|--------|---------|
| Factory adoption | 92% (35/38 routes) |
| Exception routes | 4 |
| Documented exceptions | 4 |
| Annual review | Pending |

Track exception metrics quarterly to ensure they remain justified and minimal.
