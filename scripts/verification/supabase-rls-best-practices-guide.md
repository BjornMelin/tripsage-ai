# Comprehensive Guide to Supabase Row Level Security (RLS) Best Practices

## Table of Contents
1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Best Practices for Multi-Tenant Applications](#best-practices-for-multi-tenant-applications)
4. [Performance Optimization](#performance-optimization)
5. [Testing Strategies](#testing-strategies)
6. [Common Pitfalls and Security Considerations](#common-pitfalls-and-security-considerations)
7. [Collaborative Access Patterns](#collaborative-access-patterns)
8. [Code Examples](#code-examples)
9. [Advanced Patterns](#advanced-patterns)
10. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Introduction

Row Level Security (RLS) is one of Supabase's most powerful features, allowing you to implement robust security controls directly at the database level. Unlike traditional application-level security, RLS enforces access rules within PostgreSQL itself, ensuring that users can only access the data they're authorized to see, regardless of how they connect to your application.

### Why RLS Matters

- **Security at the Data Layer**: Security rules are enforced at the database level, not just in your application code
- **Simplified Application Logic**: Your frontend code doesn't need complex filtering logic
- **Consistent Security**: Same security rules apply regardless of access method (API, direct database access, etc.)
- **Reduced Risk of Data Leaks**: Even with application bugs, the database still enforces access controls

## Core Concepts

### How RLS Works in Supabase

Supabase stores an authenticated user's JWT inside a PostgreSQL session variable via `set_config('request.jwt.claims', ...)`. Inside your policy expressions, you can reference claims such as `auth.uid()` or custom metadata. Once you `ENABLE ROW LEVEL SECURITY` on a table, PostgreSQL denies all access until at least one policy explicitly grants it.

### Basic Policy Structure

```sql
CREATE POLICY policy_name
ON table_name
FOR operation
TO role
USING (expression)
WITH CHECK (expression);
```

- `policy_name`: Descriptive name for your policy
- `table_name`: The table this policy applies to
- `operation`: Can be SELECT, INSERT, UPDATE, DELETE, or ALL
- `role`: Usually 'authenticated' or 'anon' in Supabase
- `USING`: For SELECT, UPDATE, DELETE operations (existing rows)
- `WITH CHECK`: For INSERT, UPDATE operations (new/modified rows)

## Best Practices for Multi-Tenant Applications

### 1. Tenant Isolation Pattern

The most common multi-tenant pattern involves adding a `tenant_id` column to all tenant-scoped tables:

```sql
-- Add tenant_id to your tables
ALTER TABLE projects ADD COLUMN tenant_id UUID NOT NULL;

-- Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Create tenant isolation policy
CREATE POLICY "Tenant isolation policy"
ON projects
FOR ALL
TO authenticated
USING (tenant_id = auth.jwt()->>'tenant_id')
WITH CHECK (tenant_id = auth.jwt()->>'tenant_id');
```

### 2. Using Custom Claims for Tenant Context

For better performance and security, store tenant information in JWT claims:

```sql
-- Helper function to get tenant_id from JWT
CREATE OR REPLACE FUNCTION auth.tenant_id() 
RETURNS uuid 
LANGUAGE sql 
STABLE
AS $$
  SELECT COALESCE(
    NULLIF(current_setting('request.jwt.claim.tenant_id', true), ''),
    (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'tenant_id')
  )::uuid
$$;

-- Use in policies
CREATE POLICY "Tenant members can access their data"
ON projects
FOR ALL
TO authenticated
USING (tenant_id = auth.tenant_id())
WITH CHECK (tenant_id = auth.tenant_id());
```

### 3. Session-based Tenant Context

For applications where tenant context is set per session:

```sql
-- Set tenant context at the beginning of each session
SET app.tenant_id = 'e50c1f60-1c92-11ec-9621-0242ac130002';

-- Create policy using session variable
CREATE POLICY tenant_isolation_policy
ON users
USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

## Performance Optimization

### 1. Always Index RLS Columns

The single most important optimization is to index columns used in RLS policies:

```sql
-- Index columns used in RLS policies
CREATE INDEX idx_user_id ON test_table USING btree (user_id);
CREATE INDEX idx_tenant_id ON test_table USING btree (tenant_id);
CREATE INDEX idx_organization_id ON test_table USING btree (organization_id);

-- For array columns, use GIN indexes
CREATE INDEX idx_tenant_group_ids ON test_table USING gin (tenant_group_ids);
```

Performance improvement can be over 100x on large tables with proper indexing.

### 2. Wrap Functions in SELECT Statements

Wrapping functions in SELECT statements allows PostgreSQL to cache results via `initPlan`:

```sql
-- Instead of this (slower):
CREATE POLICY "Check admin status"
ON projects
USING (is_admin() OR auth.uid() = user_id);

-- Do this (faster):
CREATE POLICY "Check admin status"
ON projects
USING ((SELECT is_admin()) OR (SELECT auth.uid()) = user_id);
```

### 3. Use Security Definer Functions

Security definer functions bypass RLS on joined tables, significantly improving performance:

```sql
-- Create a security definer function
CREATE OR REPLACE FUNCTION private.has_role(role_name text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER -- Runs with creator's privileges
SET search_path = ''
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM roles_table
    WHERE user_id = auth.uid() AND role = role_name
  );
END;
$$;

-- Use in policy (much faster than direct join)
CREATE POLICY "Role-based access"
ON sensitive_data
TO authenticated
USING ((SELECT private.has_role('admin')));
```

### 4. Optimize Join Patterns

Avoid joins in RLS policies by restructuring queries:

```sql
-- Slow pattern (join in WHERE clause):
CREATE POLICY "Team access slow"
ON test_table
TO authenticated
USING (
  auth.uid() IN (
    SELECT user_id
    FROM team_user
    WHERE team_user.team_id = test_table.team_id -- This creates a join
  )
);

-- Fast pattern (no join):
CREATE POLICY "Team access fast"
ON test_table
TO authenticated
USING (
  team_id IN (
    SELECT team_id
    FROM team_user
    WHERE user_id = auth.uid() -- No join needed
  )
);
```

### 5. Add Application-Level Filtering

Don't rely solely on RLS for filtering - add explicit filters in your queries:

```javascript
// Instead of just this:
const { data } = await supabase
  .from('projects')
  .select('*');

// Also add explicit filtering:
const { data } = await supabase
  .from('projects')
  .select('*')
  .eq('tenant_id', tenantId)
  .eq('user_id', userId);
```

### 6. Specify Target Roles

Always specify which roles a policy applies to:

```sql
-- Good - only evaluated for authenticated users
CREATE POLICY "Authenticated users only"
ON projects
TO authenticated -- Skips evaluation for anon users
USING (user_id = auth.uid());

-- Less efficient - evaluated for all roles
CREATE POLICY "All users"
ON projects
USING (auth.uid() = user_id);
```

## Testing Strategies

### 1. Use pgTAP for Automated Testing

```sql
BEGIN;
SELECT plan(3);

-- Test that RLS is enabled
SELECT tests.rls_enabled('public', 'projects');

-- Test specific policies exist
SELECT policies_are(
  'public',
  'projects',
  ARRAY[
    'Users can view their own projects',
    'Users can update their own projects'
  ]
);

-- Test policy behavior
SET LOCAL role TO authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "user-123", "tenant_id": "tenant-456"}';

-- This should return results
SELECT results_eq(
  'SELECT COUNT(*) FROM projects WHERE tenant_id = ''tenant-456''',
  'SELECT 1::bigint'
);

SELECT * FROM finish();
ROLLBACK;
```

### 2. Test in Supabase Dashboard

Use the SQL Editor with different roles:

```sql
-- Test as authenticated user
SET LOCAL role TO authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "test-user-id"}';
SELECT * FROM projects; -- Should only see user's projects

-- Test as anon user
SET LOCAL role TO anon;
SELECT * FROM projects; -- Should see nothing or public data only
```

### 3. Test View Security

Views bypass RLS by default, so test them carefully:

```javascript
// Test if your view respects RLS
const { data } = await supabase
  .from('my_view')
  .select('*');

// If you see ALL rows, your view is bypassing RLS!
// For Postgres 15+, create secure views:
CREATE VIEW public.my_view
WITH (security_invoker = true) AS
SELECT * FROM my_table;
```

## Common Pitfalls and Security Considerations

### 1. Views Bypass RLS by Default

```sql
-- For Postgres 15+
CREATE VIEW secure_user_data
WITH (security_invoker = true) AS
SELECT * FROM users
WHERE organization_id = auth.jwt()->>'org_id';

-- For older versions, use internal schema
CREATE SCHEMA internal;
CREATE VIEW internal.user_data AS
SELECT * FROM users;
-- Don't expose internal schema to API
```

### 2. Forgetting to Enable RLS

```sql
-- Always check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';

-- Enable RLS on all public tables
DO $$
DECLARE
  t text;
BEGIN
  FOR t IN 
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;
```

### 3. Missing FORCE ROW LEVEL SECURITY

```sql
-- Ensure RLS applies even to table owners
ALTER TABLE sensitive_data FORCE ROW LEVEL SECURITY;
```

### 4. Recursive RLS Calls

Avoid policies that trigger RLS on the same or related tables:

```sql
-- BAD: This can cause infinite recursion
CREATE POLICY "Check ownership"
ON documents
USING (
  owner_id IN (
    SELECT user_id FROM documents WHERE parent_id = id
  )
);

-- GOOD: Use security definer function
CREATE FUNCTION check_document_ownership(doc_id uuid)
RETURNS boolean
SECURITY DEFINER
AS $$
  -- Function logic here
$$ LANGUAGE sql;
```

## Collaborative Access Patterns

### 1. Shared Resources Pattern

For resources shared between users:

```sql
-- Create sharing table
CREATE TABLE resource_shares (
  resource_id uuid REFERENCES resources(id),
  shared_with_user_id uuid REFERENCES auth.users(id),
  permission text CHECK (permission IN ('read', 'write', 'admin')),
  PRIMARY KEY (resource_id, shared_with_user_id)
);

-- Policy for shared access
CREATE POLICY "Shared resource access"
ON resources
FOR SELECT
TO authenticated
USING (
  owner_id = auth.uid()
  OR 
  id IN (
    SELECT resource_id 
    FROM resource_shares 
    WHERE shared_with_user_id = auth.uid()
  )
);
```

### 2. Team-Based Access

```sql
-- Helper function for team membership
CREATE FUNCTION is_team_member(team_uuid uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM team_members
    WHERE team_id = team_uuid
    AND user_id = auth.uid()
    AND status = 'active'
  );
$$;

-- Use in policies
CREATE POLICY "Team members can access team resources"
ON team_resources
FOR ALL
TO authenticated
USING (is_team_member(team_id))
WITH CHECK (is_team_member(team_id));
```

### 3. Hierarchical Permissions

For nested organizational structures:

```sql
-- Recursive CTE for hierarchy
CREATE FUNCTION get_accessible_departments()
RETURNS SETOF uuid
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  WITH RECURSIVE dept_hierarchy AS (
    -- Start with user's direct departments
    SELECT department_id
    FROM user_departments
    WHERE user_id = auth.uid()
    
    UNION
    
    -- Add all child departments
    SELECT d.id
    FROM departments d
    INNER JOIN dept_hierarchy h ON d.parent_id = h.department_id
  )
  SELECT department_id FROM dept_hierarchy;
$$;

-- Use in policy
CREATE POLICY "Hierarchical department access"
ON department_data
FOR ALL
TO authenticated
USING (department_id IN (SELECT get_accessible_departments()));
```

## Code Examples

### 1. Complete Multi-Tenant Setup

```sql
-- 1. Create tenant table
CREATE TABLE tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- 2. Create user-tenant relationship
CREATE TABLE tenant_users (
  tenant_id uuid REFERENCES tenants(id),
  user_id uuid REFERENCES auth.users(id),
  role text NOT NULL DEFAULT 'member',
  PRIMARY KEY (tenant_id, user_id)
);

-- 3. Add tenant_id to all tenant-scoped tables
CREATE TABLE projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  name text NOT NULL,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now()
);

-- 4. Create helper functions
CREATE OR REPLACE FUNCTION get_user_tenant_id()
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT tenant_id 
  FROM tenant_users 
  WHERE user_id = auth.uid()
  LIMIT 1;
$$;

-- 5. Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;

-- 6. Create policies
CREATE POLICY "Tenant isolation"
ON projects
FOR ALL
TO authenticated
USING (tenant_id = get_user_tenant_id())
WITH CHECK (tenant_id = get_user_tenant_id());

-- 7. Create indexes
CREATE INDEX idx_projects_tenant_id ON projects(tenant_id);
CREATE INDEX idx_tenant_users_user_id ON tenant_users(user_id);
```

### 2. API Key Authentication Pattern

```sql
-- API tokens table
CREATE TABLE api_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(id),
  name text NOT NULL,
  token_hash text NOT NULL,
  permissions text[] DEFAULT '{}',
  expires_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Custom role for API access
CREATE ROLE api_user;
GRANT api_user TO authenticator;

-- Function to validate API token
CREATE FUNCTION validate_api_token(token text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  token_data record;
BEGIN
  SELECT t.*, tenant_id
  INTO token_data
  FROM api_tokens t
  WHERE token_hash = crypt(token, token_hash)
  AND (expires_at IS NULL OR expires_at > now());
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Invalid token';
  END IF;
  
  -- Set session variables
  PERFORM set_config('request.jwt.claims', 
    json_build_object(
      'role', 'api_user',
      'tenant_id', token_data.tenant_id,
      'permissions', token_data.permissions
    )::text, true);
    
  RETURN json_build_object('success', true);
END;
$$;

-- RLS policy for API access
CREATE POLICY "API token access"
ON projects
TO api_user
USING (
  tenant_id = (current_setting('request.jwt.claims')::json->>'tenant_id')::uuid
  AND 
  'read:projects' = ANY(
    (current_setting('request.jwt.claims')::json->>'permissions')::text[]
  )
);
```

### 3. Time-based Access Control

```sql
-- Subscription-based access
CREATE TABLE subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(id),
  plan text NOT NULL,
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_until timestamptz NOT NULL,
  is_active boolean GENERATED ALWAYS AS (
    now() BETWEEN valid_from AND valid_until
  ) STORED
);

-- Function to check active subscription
CREATE FUNCTION has_active_subscription()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM subscriptions
    WHERE tenant_id = get_user_tenant_id()
    AND is_active = true
  );
$$;

-- Policy with subscription check
CREATE POLICY "Requires active subscription"
ON premium_features
FOR ALL
TO authenticated
USING (
  tenant_id = get_user_tenant_id() 
  AND has_active_subscription()
);

-- Index for performance
CREATE INDEX idx_subscriptions_active 
ON subscriptions(tenant_id, is_active) 
WHERE is_active = true;
```

## Advanced Patterns

### 1. Attribute-Based Access Control (ABAC)

```sql
-- User attributes table
CREATE TABLE user_attributes (
  user_id uuid REFERENCES auth.users(id),
  attribute_key text NOT NULL,
  attribute_value jsonb NOT NULL,
  PRIMARY KEY (user_id, attribute_key)
);

-- Resource attributes table
CREATE TABLE resource_attributes (
  resource_id uuid NOT NULL,
  attribute_key text NOT NULL,
  attribute_value jsonb NOT NULL,
  PRIMARY KEY (resource_id, attribute_key)
);

-- ABAC evaluation function
CREATE FUNCTION evaluate_abac_policy(
  resource_id uuid,
  required_attributes jsonb
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_attrs jsonb;
  resource_attrs jsonb;
BEGIN
  -- Get user attributes
  SELECT jsonb_object_agg(attribute_key, attribute_value)
  INTO user_attrs
  FROM user_attributes
  WHERE user_id = auth.uid();
  
  -- Get resource attributes
  SELECT jsonb_object_agg(attribute_key, attribute_value)
  INTO resource_attrs
  FROM resource_attributes
  WHERE resource_id = evaluate_abac_policy.resource_id;
  
  -- Evaluate policy
  RETURN user_attrs @> required_attributes;
END;
$$;

-- Use in RLS policy
CREATE POLICY "ABAC policy"
ON sensitive_resources
FOR ALL
TO authenticated
USING (
  evaluate_abac_policy(
    id, 
    '{"clearance_level": "secret", "department": "engineering"}'::jsonb
  )
);
```

### 2. Audit-Aware RLS

```sql
-- Audit log table (no RLS)
CREATE TABLE audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name text NOT NULL,
  operation text NOT NULL,
  user_id uuid,
  record_id uuid,
  old_data jsonb,
  new_data jsonb,
  created_at timestamptz DEFAULT now()
);

-- Function to log with context
CREATE FUNCTION log_with_rls_context()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO audit_logs (
    table_name,
    operation,
    user_id,
    record_id,
    old_data,
    new_data
  ) VALUES (
    TG_TABLE_NAME,
    TG_OP,
    auth.uid(),
    COALESCE(NEW.id, OLD.id),
    to_jsonb(OLD),
    to_jsonb(NEW)
  );
  
  RETURN COALESCE(NEW, OLD);
END;
$$;

-- Apply to tables
CREATE TRIGGER audit_projects
AFTER INSERT OR UPDATE OR DELETE ON projects
FOR EACH ROW EXECUTE FUNCTION log_with_rls_context();
```

### 3. Dynamic Policy Generation

```sql
-- Policy templates table
CREATE TABLE policy_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  template_sql text NOT NULL,
  parameters jsonb DEFAULT '{}'
);

-- Function to apply dynamic policies
CREATE FUNCTION apply_dynamic_policy(
  table_name text,
  policy_template_id uuid
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  template record;
  policy_sql text;
BEGIN
  SELECT * INTO template
  FROM policy_templates
  WHERE id = policy_template_id;
  
  -- Generate policy SQL
  policy_sql := format(
    template.template_sql,
    table_name,
    template.parameters->>'role',
    template.parameters->>'condition'
  );
  
  -- Execute policy creation
  EXECUTE policy_sql;
END;
$$;
```

## Monitoring and Maintenance

### 1. Performance Monitoring

```sql
-- Monitor slow RLS queries
CREATE OR REPLACE FUNCTION monitor_rls_performance()
RETURNS TABLE (
  query text,
  calls bigint,
  total_time double precision,
  mean_time double precision,
  max_time double precision
)
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT 
    query,
    calls,
    total_exec_time as total_time,
    mean_exec_time as mean_time,
    max_exec_time as max_time
  FROM pg_stat_statements
  WHERE query LIKE '%row_security%'
  ORDER BY total_exec_time DESC
  LIMIT 20;
$$;
```

### 2. RLS Policy Audit

```sql
-- Audit all RLS policies
CREATE OR REPLACE VIEW rls_policy_audit AS
SELECT 
  n.nspname as schema_name,
  c.relname as table_name,
  pol.polname as policy_name,
  pol.polroles::regrole[] as roles,
  CASE pol.polcmd
    WHEN 'r' THEN 'SELECT'
    WHEN 'a' THEN 'INSERT'
    WHEN 'w' THEN 'UPDATE'
    WHEN 'd' THEN 'DELETE'
    WHEN '*' THEN 'ALL'
  END as operation,
  pol.polqual::text as using_expression,
  pol.polwithcheck::text as with_check_expression
FROM pg_policy pol
JOIN pg_class c ON c.oid = pol.polrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname, pol.polname;
```

### 3. Regular Maintenance Tasks

```sql
-- 1. Update statistics for RLS columns
ANALYZE projects(tenant_id, user_id);

-- 2. Check for missing indexes
SELECT 
  schemaname,
  tablename,
  attname,
  n_distinct,
  correlation
FROM pg_stats
WHERE schemaname = 'public'
AND attname IN ('tenant_id', 'user_id', 'organization_id')
AND tablename NOT IN (
  SELECT tablename 
  FROM pg_indexes 
  WHERE indexdef LIKE '%' || attname || '%'
);

-- 3. Review unused policies
CREATE FUNCTION find_unused_policies()
RETURNS TABLE (
  table_name text,
  policy_name text,
  last_used timestamptz
)
LANGUAGE sql
AS $$
  -- Implementation depends on your logging setup
  SELECT 'Implementation needed'::text, ''::text, now();
$$;
```

### 4. Security Advisors

Use Supabase's built-in security advisors:

```sql
-- Check for RLS issues
SELECT * FROM pg_stat_user_tables 
WHERE schemaname = 'public' 
AND NOT hasrls;

-- Check for tables with RLS enabled but no policies
SELECT 
  schemaname,
  tablename
FROM pg_tables t
WHERE schemaname = 'public'
AND rowsecurity = true
AND NOT EXISTS (
  SELECT 1 
  FROM pg_policies p 
  WHERE p.schemaname = t.schemaname 
  AND p.tablename = t.tablename
);
```

## Conclusion

Implementing Row Level Security effectively requires careful planning, consistent patterns, and ongoing monitoring. By following these best practices, you can build secure, performant multi-tenant applications that scale with your needs.

Key takeaways:
- Always index RLS policy columns
- Use security definer functions for complex logic
- Test policies thoroughly with automated tools
- Monitor performance and adjust as needed
- Keep policies simple and focused
- Document your security model clearly

Remember that RLS is a powerful tool, but it's not a silver bullet. Combine it with other security measures like API rate limiting, proper authentication, and regular security audits for a comprehensive security strategy.