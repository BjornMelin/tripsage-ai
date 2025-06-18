# Supabase Troubleshooting Guide

This guide helps resolve common issues when working with the TripSage Supabase infrastructure.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Migration Problems](#migration-problems)
- [Edge Function Errors](#edge-function-errors)
- [Authentication Issues](#authentication-issues)
- [Storage Problems](#storage-problems)
- [Performance Issues](#performance-issues)
- [RLS Policy Errors](#rls-policy-errors)
- [Local Development Issues](#local-development-issues)
- [Production Deployment Issues](#production-deployment-issues)
- [Common Error Messages](#common-error-messages)

## Connection Issues

### Cannot connect to Supabase

**Symptoms:**

- `ECONNREFUSED` errors
- `Connection timeout` messages
- `Invalid API key` errors

**Solutions:**

1. **Check environment variables:**

   ```bash
   # Verify variables are set
   echo $SUPABASE_URL
   echo $SUPABASE_ANON_KEY
   
   # Ensure no trailing slashes in URL
   # ✅ Correct: https://project.supabase.co
   # ❌ Wrong: https://project.supabase.co/
   ```

2. **Test connection:**

   ```bash
   # Test API endpoint
   curl -H "apikey: $SUPABASE_ANON_KEY" \
        -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
        $SUPABASE_URL/rest/v1/
   ```

3. **Check project status:**
   - Visit Supabase dashboard
   - Ensure project is not paused
   - Check for ongoing maintenance

### Database connection pool exhausted

**Symptoms:**

- `too many connections` error
- Intermittent connection failures
- Slow query performance

**Solutions:**

1. **Use connection pooling:**

   ```javascript
   // Use pooler URL for applications
   const DATABASE_URL = process.env.DATABASE_POOLER_URL;
   ```

2. **Configure pool settings:**

   ```javascript
   // Supabase client configuration
   const supabase = createClient(url, key, {
     db: {
       schema: 'public',
     },
     auth: {
       persistSession: true,
       autoRefreshToken: true,
     },
     global: {
       headers: {
         'x-connection-pooling': 'true'
       }
     }
   });
   ```

3. **Monitor connections:**

   ```sql
   -- Check active connections
   SELECT count(*) FROM pg_stat_activity;
   
   -- View connection details
   SELECT pid, usename, application_name, state 
   FROM pg_stat_activity 
   WHERE state = 'active';
   ```

## Migration Problems

### Migration fails to apply

**Symptoms:**

- `permission denied` errors
- `relation already exists` errors
- Migration stuck in pending state

**Solutions:**

1. **Check migration status:**

   ```bash
   # List migrations
   supabase migration list
   
   # Check current schema
   supabase db dump --schema-only > current_schema.sql
   ```

2. **Fix permission issues:**

   ```sql
   -- Grant necessary permissions
   GRANT ALL ON SCHEMA public TO postgres;
   GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
   GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
   ```

3. **Handle duplicate objects:**

   ```sql
   -- Make migrations idempotent
   CREATE TABLE IF NOT EXISTS table_name (...);
   CREATE INDEX IF NOT EXISTS index_name ON table_name (...);
   ALTER TABLE table_name ADD COLUMN IF NOT EXISTS column_name type;
   ```

4. **Reset migrations (development only):**

   ```bash
   # Reset to clean state
   supabase db reset
   
   # Apply specific migration
   supabase migration up --file 20250617_initial_schema.sql
   ```

### Migration rollback needed

**Symptoms:**

- Schema in inconsistent state
- Application errors after migration
- Need to revert changes

**Solutions:**

1. **Create rollback migration:**

   ```sql
   -- Rollback file: 20250617_rollback_feature.sql
   BEGIN;
   
   -- Reverse the changes
   DROP TABLE IF EXISTS new_table;
   ALTER TABLE existing_table DROP COLUMN IF EXISTS new_column;
   DROP INDEX IF EXISTS new_index;
   
   COMMIT;
   ```

2. **Use transaction safety:**

   ```sql
   -- Wrap migrations in transactions
   BEGIN;
   
   -- Your migration changes
   
   -- Test with a query
   SELECT 1 FROM new_table LIMIT 1;
   
   COMMIT; -- or ROLLBACK if issues
   ```

## Edge Function Errors

### Function deployment fails

**Symptoms:**

- `Deployment failed` message
- TypeScript compilation errors
- Missing dependencies

**Solutions:**

1. **Check function syntax:**

   ```bash
   # Validate TypeScript
   deno check supabase/functions/function-name/index.ts
   
   # Run type checking
   deno task check
   ```

2. **Fix import issues:**

   ```typescript
   // Use proper import syntax
   import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
   
   // For Supabase imports
   import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
   ```

3. **Set required secrets:**

   ```bash
   # List current secrets
   supabase secrets list
   
   # Set missing secrets
   supabase secrets set OPENAI_API_KEY=sk-...
   supabase secrets set RESEND_API_KEY=re_...
   ```

### Function returns 500 error

**Symptoms:**

- Internal server error responses
- No detailed error message
- Function crashes

**Solutions:**

1. **Add error handling:**

   ```typescript
   serve(async (req) => {
     try {
       // Your function logic
       return new Response(JSON.stringify(result), {
         headers: { ...corsHeaders, "Content-Type": "application/json" },
         status: 200,
       });
     } catch (error) {
       console.error('Function error:', error);
       return new Response(
         JSON.stringify({ 
           error: error.message,
           details: process.env.NODE_ENV === 'development' ? error.stack : undefined
         }),
         { 
           headers: { ...corsHeaders, "Content-Type": "application/json" },
           status: 500,
         }
       );
     }
   });
   ```

2. **Check logs:**

   ```bash
   # View function logs
   supabase functions logs function-name
   
   # Follow logs in real-time
   supabase functions logs function-name --follow
   ```

3. **Test locally:**

   ```bash
   # Serve functions locally
   supabase functions serve function-name
   
   # Test with curl
   curl -i --location --request POST \
     'http://localhost:54321/functions/v1/function-name' \
     --header 'Authorization: Bearer '$SUPABASE_ANON_KEY \
     --header 'Content-Type: application/json' \
     --data '{"test": "data"}'
   ```

### CORS errors

**Symptoms:**

- `Access-Control-Allow-Origin` errors
- Preflight request failures
- Cross-origin blocked

**Solutions:**

1. **Implement proper CORS handling:**

   ```typescript
   const corsHeaders = {
     'Access-Control-Allow-Origin': '*',
     'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
     'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, PUT, DELETE',
   };
   
   serve(async (req) => {
     // Handle OPTIONS request
     if (req.method === 'OPTIONS') {
       return new Response('ok', { headers: corsHeaders });
     }
     
     // Your function logic
     return new Response(JSON.stringify(data), {
       headers: { ...corsHeaders, 'Content-Type': 'application/json' },
       status: 200,
     });
   });
   ```

2. **Configure allowed origins:**

   ```typescript
   const allowedOrigins = [
     'http://localhost:3000',
     'https://tripsage.com',
     'https://*.tripsage.com'
   ];
   
   const origin = req.headers.get('origin') || '';
   const corsHeaders = {
     'Access-Control-Allow-Origin': allowedOrigins.includes(origin) ? origin : '',
     // ... other headers
   };
   ```

## Authentication Issues

### Login fails silently

**Symptoms:**

- No error message on login
- User not redirected after login
- Session not persisted

**Solutions:**

1. **Check redirect URLs:**

   ```javascript
   // Ensure correct redirect URL
   const { data, error } = await supabase.auth.signInWithOAuth({
     provider: 'google',
     options: {
       redirectTo: `${window.location.origin}/auth/callback`
     }
   });
   ```

2. **Verify site URL configuration:**
   - Go to Supabase Dashboard > Authentication > URL Configuration
   - Add all valid redirect URLs
   - Include localhost for development

3. **Handle auth state changes:**

   ```javascript
   // Listen for auth changes
   useEffect(() => {
     const { data: authListener } = supabase.auth.onAuthStateChange(
       async (event, session) => {
         console.log('Auth event:', event);
         if (event === 'SIGNED_IN') {
           // Handle successful login
         } else if (event === 'SIGNED_OUT') {
           // Handle logout
         }
       }
     );
     
     return () => {
       authListener.subscription.unsubscribe();
     };
   }, []);
   ```

### JWT token expired

**Symptoms:**

- `JWT expired` error
- Unauthorized requests
- User logged out unexpectedly

**Solutions:**

1. **Enable auto-refresh:**

   ```javascript
   const supabase = createClient(url, key, {
     auth: {
       autoRefreshToken: true,
       persistSession: true,
       detectSessionInUrl: true
     }
   });
   ```

2. **Manually refresh token:**

   ```javascript
   // Force token refresh
   const { data, error } = await supabase.auth.refreshSession();
   if (error) {
     // Handle refresh failure - user needs to log in again
     await supabase.auth.signOut();
     redirect('/login');
   }
   ```

3. **Check token validity:**

   ```javascript
   // Get current session
   const { data: { session }, error } = await supabase.auth.getSession();
   
   if (session) {
     // Check if token is about to expire
     const expiresAt = session.expires_at;
     const now = Math.floor(Date.now() / 1000);
     const timeUntilExpiry = expiresAt - now;
     
     if (timeUntilExpiry < 300) { // Less than 5 minutes
       await supabase.auth.refreshSession();
     }
   }
   ```

## Storage Problems

### File upload fails

**Symptoms:**

- `Request Entity Too Large` error
- `Invalid file type` error
- Upload timeout

**Solutions:**

1. **Check file size limits:**

   ```javascript
   // Validate before upload
   const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
   
   if (file.size > MAX_FILE_SIZE) {
     throw new Error('File too large. Maximum size is 50MB.');
   }
   ```

2. **Verify MIME types:**

   ```javascript
   const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
   
   if (!ALLOWED_TYPES.includes(file.type)) {
     throw new Error(`File type ${file.type} not allowed`);
   }
   ```

3. **Use proper upload method:**

   ```javascript
   // For large files, use resumable upload
   const { data, error } = await supabase.storage
     .from('attachments')
     .upload(fileName, file, {
       cacheControl: '3600',
       upsert: false,
       duplex: 'half' // For Node.js 20+
     });
   ```

### Storage bucket not accessible

**Symptoms:**

- `Bucket not found` error
- Permission denied on file access
- Public URLs not working

**Solutions:**

1. **Create bucket if missing:**

   ```sql
   -- Create storage bucket
   INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
   VALUES (
     'attachments',
     'attachments',
     false,
     52428800, -- 50MB
     ARRAY['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
   );
   ```

2. **Set bucket policies:**

   ```sql
   -- Allow authenticated users to upload
   CREATE POLICY "Allow authenticated uploads" ON storage.objects
   FOR INSERT TO authenticated
   WITH CHECK (bucket_id = 'attachments' AND auth.uid()::text = (storage.foldername(name))[1]);
   
   -- Allow users to view their own files
   CREATE POLICY "Allow user file access" ON storage.objects
   FOR SELECT TO authenticated
   USING (bucket_id = 'attachments' AND auth.uid()::text = (storage.foldername(name))[1]);
   ```

3. **Generate signed URLs for private files:**

   ```javascript
   // Get temporary signed URL
   const { data, error } = await supabase.storage
     .from('attachments')
     .createSignedUrl(filePath, 3600); // 1 hour expiry
   ```

## Performance Issues

### Slow query performance

**Symptoms:**

- Queries taking >1 second
- Application timeouts
- High database CPU usage

**Solutions:**

1. **Add appropriate indexes:**

   ```sql
   -- Check missing indexes
   SELECT schemaname, tablename, attname, n_distinct, correlation
   FROM pg_stats
   WHERE tablename = 'trips'
   AND n_distinct > 100
   AND correlation < 0.1
   ORDER BY n_distinct DESC;
   
   -- Create indexes for common queries
   CREATE INDEX idx_trips_user_id_created_at 
   ON trips(user_id, created_at DESC);
   
   CREATE INDEX idx_flights_trip_id_departure 
   ON flights(trip_id, departure_date);
   ```

2. **Analyze query plans:**

   ```sql
   -- Check query execution plan
   EXPLAIN ANALYZE
   SELECT t.*, f.* 
   FROM trips t
   LEFT JOIN flights f ON f.trip_id = t.id
   WHERE t.user_id = 'uuid'
   ORDER BY t.created_at DESC
   LIMIT 10;
   ```

3. **Optimize RLS policies:**

   ```sql
   -- Inefficient policy
   CREATE POLICY "bad_policy" ON trips
   USING (
     auth.uid() IN (
       SELECT user_id FROM trip_collaborators WHERE trip_id = trips.id
     )
   );
   
   -- Optimized policy
   CREATE POLICY "good_policy" ON trips
   USING (
     user_id = auth.uid() 
     OR EXISTS (
       SELECT 1 FROM trip_collaborators tc
       WHERE tc.trip_id = trips.id 
       AND tc.user_id = auth.uid()
     )
   );
   ```

### Vector search slow

**Symptoms:**

- Embedding queries taking >500ms
- Memory search timeouts
- High memory usage

**Solutions:**

1. **Create proper vector indexes:**

   ```sql
   -- Create IVFFlat index for better performance
   CREATE INDEX memories_embedding_idx ON memories 
   USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   
   -- For smaller datasets, use HNSW
   CREATE INDEX memories_embedding_hnsw_idx ON memories 
   USING hnsw (embedding vector_cosine_ops);
   ```

2. **Optimize search queries:**

   ```sql
   -- Limit search scope
   SELECT content, 1 - (embedding <=> $1) as similarity
   FROM memories
   WHERE user_id = auth.uid()
     AND created_at > NOW() - INTERVAL '90 days'
   ORDER BY embedding <=> $1
   LIMIT 10;
   ```

3. **Tune vector parameters:**

   ```sql
   -- Set index parameters
   ALTER INDEX memories_embedding_idx 
   SET (maintenance_work_mem = '512MB');
   
   -- Adjust probes for accuracy/speed trade-off
   SET ivfflat.probes = 10; -- Default is 1
   ```

## RLS Policy Errors

### Permission denied errors

**Symptoms:**

- `new row violates row-level security policy` error
- Cannot read/write data despite being authenticated
- Inconsistent access permissions

**Solutions:**

1. **Debug RLS policies:**

   ```sql
   -- Check which policies apply
   SELECT * FROM pg_policies 
   WHERE tablename = 'trips';
   
   -- Test policy as specific user
   SET ROLE authenticated;
   SET request.jwt.claims ->> 'sub' = 'user-uuid';
   
   -- Try the query
   SELECT * FROM trips;
   
   -- Reset role
   RESET ROLE;
   ```

2. **Fix common policy issues:**

   ```sql
   -- Ensure INSERT policies exist
   CREATE POLICY "Users can create trips" ON trips
   FOR INSERT TO authenticated
   WITH CHECK (auth.uid() = user_id);
   
   -- Fix UPDATE policies
   CREATE POLICY "Users can update own trips" ON trips
   FOR UPDATE TO authenticated
   USING (auth.uid() = user_id)
   WITH CHECK (auth.uid() = user_id);
   ```

3. **Handle service role operations:**

   ```javascript
   // Use service role client for admin operations
   const supabaseAdmin = createClient(
     process.env.SUPABASE_URL,
     process.env.SUPABASE_SERVICE_ROLE_KEY,
     {
       auth: {
         autoRefreshToken: false,
         persistSession: false
       }
     }
   );
   
   // This bypasses RLS
   const { data, error } = await supabaseAdmin
     .from('trips')
     .select('*');
   ```

## Local Development Issues

### Supabase CLI won't start

**Symptoms:**

- `supabase start` hangs
- Docker errors
- Port conflicts

**Solutions:**

1. **Check Docker:**

   ```bash
   # Ensure Docker is running
   docker ps
   
   # Check Docker resources
   docker system df
   
   # Clean up if needed
   docker system prune -a
   ```

2. **Fix port conflicts:**

   ```bash
   # Check ports in use
   lsof -i :54321  # Supabase API
   lsof -i :54322  # PostgreSQL
   lsof -i :54323  # Supabase Studio
   
   # Kill conflicting processes
   kill -9 $(lsof -t -i :54321)
   ```

3. **Reset local environment:**

   ```bash
   # Stop and clean
   supabase stop --no-backup
   
   # Remove volumes
   docker volume prune
   
   # Start fresh
   supabase start
   ```

### Cannot access Supabase Studio

**Symptoms:**

- Studio URL not working
- Blank page in browser
- Authentication loop

**Solutions:**

1. **Check studio status:**

   ```bash
   # Get local URLs
   supabase status
   
   # Should show:
   # Studio URL: http://localhost:54323
   ```

2. **Clear browser data:**
   - Clear cookies for localhost:54323
   - Try incognito/private mode
   - Disable browser extensions

3. **Access directly:**

   ```bash
   # Port forward if needed
   kubectl port-forward service/supabase-studio 54323:3000
   ```

## Production Deployment Issues

### Deployment fails

**Symptoms:**

- GitHub Action failures
- Migration errors in production
- Function deployment errors

**Solutions:**

1. **Check deployment logs:**

   ```bash
   # View deployment status
   supabase projects list
   
   # Check function logs
   supabase functions logs --project-ref your-project-ref
   ```

2. **Validate before deployment:**

   ```bash
   # Test migrations locally
   supabase db reset
   
   # Validate functions
   deno task test
   
   # Check for secrets
   supabase secrets list --project-ref your-project-ref
   ```

3. **Fix common deployment issues:**

   ```yaml
   # .github/workflows/deploy.yml
   - name: Deploy to Supabase
     env:
       SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
       SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}
     run: |
       # Link to project
       supabase link --project-ref $SUPABASE_PROJECT_ID
       
       # Deploy database first
       supabase db push
       
       # Then deploy functions
       supabase functions deploy
   ```

### Production data issues

**Symptoms:**

- Missing data after deployment
- Inconsistent state
- Failed migrations

**Solutions:**

1. **Backup before changes:**

   ```bash
   # Create backup
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migrations safely:**

   ```sql
   -- Use transactions
   BEGIN;
   
   -- Run migration
   \i migration.sql
   
   -- Verify data
   SELECT COUNT(*) FROM affected_table;
   
   -- Commit only if safe
   COMMIT; -- or ROLLBACK
   ```

3. **Monitor after deployment:**

   ```sql
   -- Check for errors
   SELECT * FROM postgres_log 
   WHERE error_severity = 'ERROR'
   AND log_time > NOW() - INTERVAL '1 hour';
   
   -- Monitor performance
   SELECT * FROM pg_stat_statements
   ORDER BY total_time DESC
   LIMIT 10;
   ```

## Common Error Messages

### "JWT expired"

- **Cause**: Authentication token has expired
- **Solution**: Refresh the token or re-authenticate

### "New row violates row-level security policy"

- **Cause**: RLS policy preventing operation
- **Solution**: Check and update RLS policies

### "permission denied for schema public"

- **Cause**: Missing database permissions
- **Solution**: Grant appropriate permissions to the role

### "too many connections for role"

- **Cause**: Connection pool exhausted
- **Solution**: Use pooled connection string or increase limits

### "function does not exist"

- **Cause**: Missing PostgreSQL extension or function
- **Solution**: Install required extensions or create missing functions

### "CORS policy: No 'Access-Control-Allow-Origin'"

- **Cause**: Missing CORS headers in edge function
- **Solution**: Add proper CORS headers to function response

### "Request failed with status code 524"

- **Cause**: Edge function timeout (>30s)
- **Solution**: Optimize function or use background jobs

### "invalid input syntax for type uuid"

- **Cause**: Malformed UUID in query
- **Solution**: Validate UUID format before queries

## Getting Help

If you can't resolve an issue:

1. **Check Supabase Status**: <https://status.supabase.com>
2. **Search GitHub Issues**: <https://github.com/supabase/supabase/issues>
3. **Community Discord**: <https://discord.supabase.com>
4. **Official Documentation**: <https://supabase.com/docs>
5. **Support Ticket**: <support@supabase.com> (for paid plans)

When reporting issues, include:

- Error messages and stack traces
- Environment (local/staging/production)
- Steps to reproduce
- Relevant code snippets
- Supabase CLI version (`supabase --version`)

---

**Last Updated**: 2025-06-17  
**Maintained By**: TripSage Development Team
