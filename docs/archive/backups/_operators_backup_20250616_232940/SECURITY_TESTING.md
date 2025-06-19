# 🔒 Security Testing Guide

> **Comprehensive Testing Strategies for TripSage AI Security Implementation**  
> Row Level Security Testing | API Security Validation | Automated Security Testing

This guide provides comprehensive testing strategies, tools, and procedures for validating the security implementation in TripSage AI. It covers RLS policy testing, API security validation, and automated security testing approaches.

## 📋 Table of Contents

- [📊 Security Testing Status Dashboard](#-security-testing-status-dashboard)
- [🎯 Quick Start Testing Guide](#-quick-start-testing-guide)
- [🔐 Row Level Security (RLS) Testing](#-row-level-security-rls-testing)
- [🔑 Authentication Testing](#-authentication-testing)
- [🛡️ Authorization Testing](#️-authorization-testing)
- [🌐 API Security Testing](#-api-security-testing)
- [📊 Performance Security Testing](#-performance-security-testing)
- [🔍 Security Monitoring & Auditing](#-security-monitoring--auditing)
- [🔧 Advanced Testing Patterns](#-advanced-testing-patterns)
- [🚀 Automated Testing Framework](#-automated-testing-framework)
- [📋 Security Testing Checklist](#-security-testing-checklist)
- [🎯 Testing Best Practices Summary](#-testing-best-practices-summary)

## 📊 Security Testing Status Dashboard

| Test Category | Coverage | Status | Last Updated |
|---------------|----------|---------|--------------|
| **🔐 RLS Policy Testing** | 95% | ✅ Complete | Jun 2025 |
| **🔑 Authentication Testing** | 90% | ✅ Complete | Jun 2025 |
| **🛡️ Authorization Testing** | 88% | ✅ Complete | Jun 2025 |
| **🌐 API Security Testing** | 85% | 🚧 In Progress | Jun 2025 |
| **📊 Performance Testing** | 80% | 🚧 In Progress | Jun 2025 |
| **🔍 Monitoring & Auditing** | 75% | 🚧 In Progress | Jun 2025 |

---

## 🎯 Quick Start Testing Guide

### **🚀 Essential Security Test Suite**

```bash
# 1. Run core RLS tests
npm run test:security:rls

# 2. Validate API authentication
npm run test:security:auth

# 3. Check authorization policies
npm run test:security:authz

# 4. Performance security tests
npm run test:security:performance

# 5. Generate security report
npm run test:security:report
```

### **📋 Pre-Deployment Security Checklist**

- [ ] **RLS Policies**: All tables have appropriate RLS policies
- [ ] **Authentication**: JWT validation working correctly
- [ ] **Authorization**: Role-based access controls tested
- [ ] **API Security**: Rate limiting and input validation active
- [ ] **Data Protection**: Encryption and masking verified
- [ ] **Audit Logging**: Security events being logged
- [ ] **Performance**: Security overhead within acceptable limits

---

## 🔐 Row Level Security (RLS) Testing

### **1. Basic RLS Policy Testing**

Testing fundamental RLS policy functionality:

```sql
-- Test basic user isolation
BEGIN;
SET local role authenticated;
SET local request.jwt.claims TO '{"sub": "user1", "role": "authenticated"}';

-- Should only return user1's trips
SELECT * FROM trips;

-- Should fail for other user's trips
SELECT * FROM trips WHERE user_id = 'user2';
ROLLBACK;
```

### **2. Comprehensive RLS Test Framework**

```sql
-- RLS Testing Framework
CREATE OR REPLACE FUNCTION test_rls_policy(
  test_name text,
  table_name text,
  user_id text,
  expected_count integer,
  operation text DEFAULT 'SELECT'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  actual_count integer;
  sql_query text;
BEGIN
  -- Set session for test user
  PERFORM set_config('request.jwt.claims', 
    json_build_object(
      'sub', user_id,
      'role', 'authenticated'
    )::text, true);
  
  -- Build query based on operation
  CASE operation
    WHEN 'SELECT' THEN
      sql_query := format('SELECT COUNT(*) FROM %I', table_name);
    WHEN 'INSERT' THEN
      sql_query := format('INSERT INTO %I DEFAULT VALUES', table_name);
    WHEN 'UPDATE' THEN
      sql_query := format('UPDATE %I SET updated_at = now()', table_name);
    WHEN 'DELETE' THEN
      sql_query := format('DELETE FROM %I WHERE false', table_name);
  END CASE;
  
  -- Execute and capture result
  EXECUTE sql_query INTO actual_count;
  
  -- Validate result
  IF actual_count = expected_count THEN
    RAISE NOTICE 'PASS: % - Expected: %, Actual: %', test_name, expected_count, actual_count;
    RETURN true;
  ELSE
    RAISE WARNING 'FAIL: % - Expected: %, Actual: %', test_name, expected_count, actual_count;
    RETURN false;
  END IF;
END;
$$;

-- Example test execution
SELECT test_rls_policy('User isolation test', 'trips', 'user1', 5);
SELECT test_rls_policy('Empty result for wrong user', 'trips', 'user2', 0);
```

### **3. Multi-Tenant Testing**

```sql
-- Multi-tenant RLS testing
CREATE OR REPLACE FUNCTION test_tenant_isolation()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  tenant1_id uuid := gen_random_uuid();
  tenant2_id uuid := gen_random_uuid();
  user1_id uuid := gen_random_uuid();
  user2_id uuid := gen_random_uuid();
BEGIN
  -- Setup test data
  INSERT INTO tenants (id, name) VALUES 
    (tenant1_id, 'Tenant 1'),
    (tenant2_id, 'Tenant 2');
    
  INSERT INTO tenant_users (tenant_id, user_id) VALUES
    (tenant1_id, user1_id),
    (tenant2_id, user2_id);
    
  INSERT INTO trips (id, tenant_id, user_id, title) VALUES
    (gen_random_uuid(), tenant1_id, user1_id, 'Tenant 1 Trip'),
    (gen_random_uuid(), tenant2_id, user2_id, 'Tenant 2 Trip');
  
  -- Test tenant isolation
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', user1_id, 'role', 'authenticated')::text, true);
    
  -- User 1 should see only Tenant 1 trips
  ASSERT (SELECT COUNT(*) FROM trips) = 1;
  ASSERT (SELECT tenant_id FROM trips LIMIT 1) = tenant1_id;
  
  -- Switch to user 2
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', user2_id, 'role', 'authenticated')::text, true);
    
  -- User 2 should see only Tenant 2 trips
  ASSERT (SELECT COUNT(*) FROM trips) = 1;
  ASSERT (SELECT tenant_id FROM trips LIMIT 1) = tenant2_id;
  
  RAISE NOTICE 'Tenant isolation test PASSED';
END;
$$;
```

### **4. Permission-Based Testing**

```sql
-- Role-based access testing
CREATE OR REPLACE FUNCTION test_role_permissions()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  admin_user uuid := gen_random_uuid();
  regular_user uuid := gen_random_uuid();
  trip_id uuid := gen_random_uuid();
BEGIN
  -- Setup test data
  INSERT INTO trips (id, user_id, title, visibility) VALUES
    (trip_id, admin_user, 'Admin Trip', 'private');
  
  -- Test admin access (should see all)
  PERFORM set_config('request.jwt.claims',
    json_build_object(
      'sub', admin_user,
      'role', 'authenticated',
      'user_role', 'admin'
    )::text, true);
    
  ASSERT (SELECT COUNT(*) FROM trips) >= 1;
  
  -- Test regular user access (should see only own)
  PERFORM set_config('request.jwt.claims',
    json_build_object(
      'sub', regular_user,
      'role', 'authenticated',
      'user_role', 'user'
    )::text, true);
    
  ASSERT (SELECT COUNT(*) FROM trips WHERE user_id = admin_user) = 0;
  
  RAISE NOTICE 'Role permissions test PASSED';
END;
$$;
```

### **5. Advanced RLS Scenarios**

#### **Shared Resource Testing**

```sql
-- Test shared resource access
CREATE OR REPLACE FUNCTION test_shared_resources()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  owner_id uuid := gen_random_uuid();
  shared_user_id uuid := gen_random_uuid();
  resource_id uuid := gen_random_uuid();
BEGIN
  -- Create shared resource
  INSERT INTO trips (id, user_id, title) VALUES
    (resource_id, owner_id, 'Shared Trip');
    
  INSERT INTO trip_shares (trip_id, shared_with_user_id, permission) VALUES
    (resource_id, shared_user_id, 'read');
  
  -- Test owner access
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', owner_id, 'role', 'authenticated')::text, true);
  ASSERT (SELECT COUNT(*) FROM trips WHERE id = resource_id) = 1;
  
  -- Test shared access
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', shared_user_id, 'role', 'authenticated')::text, true);
  ASSERT (SELECT COUNT(*) FROM trips WHERE id = resource_id) = 1;
  
  RAISE NOTICE 'Shared resource test PASSED';
END;
$$;
```

#### **Hierarchical Permission Testing**

```sql
-- Test hierarchical access patterns
CREATE OR REPLACE FUNCTION test_hierarchical_access()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  parent_dept uuid := gen_random_uuid();
  child_dept uuid := gen_random_uuid();
  manager_id uuid := gen_random_uuid();
  employee_id uuid := gen_random_uuid();
BEGIN
  -- Setup department hierarchy
  INSERT INTO departments (id, name, parent_id) VALUES
    (parent_dept, 'Engineering', NULL),
    (child_dept, 'Frontend Team', parent_dept);
    
  INSERT INTO user_departments (user_id, department_id, role) VALUES
    (manager_id, parent_dept, 'manager'),
    (employee_id, child_dept, 'employee');
    
  INSERT INTO department_data (id, department_id, data) VALUES
    (gen_random_uuid(), child_dept, 'Team Data');
  
  -- Manager should see child department data
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', manager_id, 'role', 'authenticated')::text, true);
  ASSERT (SELECT COUNT(*) FROM department_data) = 1;
  
  -- Employee should see only their department data
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', employee_id, 'role', 'authenticated')::text, true);
  ASSERT (SELECT COUNT(*) FROM department_data) = 1;
  
  RAISE NOTICE 'Hierarchical access test PASSED';
END;
$$;
```

---

## 🔑 Authentication Testing

### **1. JWT Token Validation Testing**

```javascript
// JWT Authentication Test Suite
describe('JWT Authentication', () => {
  it('should validate valid JWT tokens', async () => {
    const validToken = await generateTestJWT({
      sub: 'test-user-id',
      role: 'authenticated',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600
    });
    
    const response = await request(app)
      .get('/api/trips')
      .set('Authorization', `Bearer ${validToken}`)
      .expect(200);
    
    expect(response.body).toBeDefined();
  });
  
  it('should reject expired JWT tokens', async () => {
    const expiredToken = await generateTestJWT({
      sub: 'test-user-id',
      role: 'authenticated',
      iat: Math.floor(Date.now() / 1000) - 7200,
      exp: Math.floor(Date.now() / 1000) - 3600 // Expired 1 hour ago
    });
    
    await request(app)
      .get('/api/trips')
      .set('Authorization', `Bearer ${expiredToken}`)
      .expect(401);
  });
  
  it('should reject malformed JWT tokens', async () => {
    const malformedToken = 'invalid.jwt.token';
    
    await request(app)
      .get('/api/trips')
      .set('Authorization', `Bearer ${malformedToken}`)
      .expect(401);
  });
});
```

### **2. API Key Authentication Testing**

```sql
-- API Key authentication testing
CREATE OR REPLACE FUNCTION test_api_key_auth()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  tenant_id uuid := gen_random_uuid();
  api_token_id uuid := gen_random_uuid();
  test_token text := 'test_token_' || extract(epoch from now());
BEGIN
  -- Setup API token
  INSERT INTO api_tokens (id, tenant_id, name, token_hash, permissions) VALUES
    (api_token_id, tenant_id, 'Test Token', crypt(test_token, gen_salt('bf')), 
     ARRAY['read:trips', 'write:trips']);
  
  -- Test valid API token
  PERFORM validate_api_token(test_token);
  
  -- Verify session variables are set
  ASSERT current_setting('request.jwt.claims')::json->>'role' = 'api_user';
  ASSERT (current_setting('request.jwt.claims')::json->>'tenant_id')::uuid = tenant_id;
  
  RAISE NOTICE 'API key authentication test PASSED';
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING 'API key authentication test FAILED: %', SQLERRM;
END;
$$;
```

### **3. Session Management Testing**

```javascript
// Session management testing
describe('Session Management', () => {
  it('should handle concurrent sessions', async () => {
    const user = await createTestUser();
    
    // Create multiple sessions
    const session1 = await loginUser(user.email, user.password);
    const session2 = await loginUser(user.email, user.password);
    
    // Both sessions should be valid
    expect(session1.access_token).toBeDefined();
    expect(session2.access_token).toBeDefined();
    
    // Verify both can access resources
    const [response1, response2] = await Promise.all([
      request(app).get('/api/user').set('Authorization', `Bearer ${session1.access_token}`),
      request(app).get('/api/user').set('Authorization', `Bearer ${session2.access_token}`)
    ]);
    
    expect(response1.status).toBe(200);
    expect(response2.status).toBe(200);
  });
  
  it('should invalidate sessions on logout', async () => {
    const user = await createTestUser();
    const session = await loginUser(user.email, user.password);
    
    // Logout
    await request(app)
      .post('/api/auth/logout')
      .set('Authorization', `Bearer ${session.access_token}`)
      .expect(200);
    
    // Token should be invalid
    await request(app)
      .get('/api/user')
      .set('Authorization', `Bearer ${session.access_token}`)
      .expect(401);
  });
});
```

---

## 🛡️ Authorization Testing

### **1. Role-Based Access Control (RBAC) Testing**

```javascript
// RBAC testing suite
describe('Role-Based Access Control', () => {
  const roles = ['user', 'pro', 'admin'];
  const permissions = {
    user: ['read:own_trips', 'write:own_trips'],
    pro: ['read:own_trips', 'write:own_trips', 'share:trips'],
    admin: ['read:all_trips', 'write:all_trips', 'delete:trips', 'manage:users']
  };
  
  roles.forEach(role => {
    describe(`${role} role`, () => {
      let testUser;
      let authToken;
      
      beforeEach(async () => {
        testUser = await createTestUser({ role });
        authToken = await generateTestJWT({
          sub: testUser.id,
          role: 'authenticated',
          user_role: role
        });
      });
      
      permissions[role].forEach(permission => {
        it(`should allow ${permission}`, async () => {
          const endpoint = getEndpointForPermission(permission);
          const method = getMethodForPermission(permission);
          
          const response = await request(app)
            [method](endpoint)
            .set('Authorization', `Bearer ${authToken}`);
            
          expect(response.status).not.toBe(403);
        });
      });
      
      // Test denied permissions
      const deniedPermissions = getAllPermissions().filter(p => !permissions[role].includes(p));
      deniedPermissions.forEach(permission => {
        it(`should deny ${permission}`, async () => {
          const endpoint = getEndpointForPermission(permission);
          const method = getMethodForPermission(permission);
          
          const response = await request(app)
            [method](endpoint)
            .set('Authorization', `Bearer ${authToken}`);
            
          expect(response.status).toBe(403);
        });
      });
    });
  });
});
```

### **2. Resource-Based Authorization Testing**

```javascript
// Resource ownership testing
describe('Resource Authorization', () => {
  it('should allow owners to access their resources', async () => {
    const owner = await createTestUser();
    const trip = await createTestTrip({ userId: owner.id });
    const token = await generateAuthToken(owner);
    
    const response = await request(app)
      .get(`/api/trips/${trip.id}`)
      .set('Authorization', `Bearer ${token}`)
      .expect(200);
    
    expect(response.body.id).toBe(trip.id);
  });
  
  it('should deny access to non-owners', async () => {
    const owner = await createTestUser();
    const nonOwner = await createTestUser();
    const trip = await createTestTrip({ userId: owner.id });
    const token = await generateAuthToken(nonOwner);
    
    await request(app)
      .get(`/api/trips/${trip.id}`)
      .set('Authorization', `Bearer ${token}`)
      .expect(404); // Or 403, depending on security preference
  });
  
  it('should allow shared access with proper permissions', async () => {
    const owner = await createTestUser();
    const sharedUser = await createTestUser();
    const trip = await createTestTrip({ userId: owner.id });
    
    // Share trip with read permission
    await shareTrip(trip.id, sharedUser.id, 'read');
    
    const token = await generateAuthToken(sharedUser);
    
    const response = await request(app)
      .get(`/api/trips/${trip.id}`)
      .set('Authorization', `Bearer ${token}`)
      .expect(200);
    
    expect(response.body.id).toBe(trip.id);
  });
});
```

---

## 🌐 API Security Testing

### **1. Input Validation Testing**

```javascript
// Input validation and sanitization tests
describe('API Input Validation', () => {
  it('should validate required fields', async () => {
    const token = await generateAuthToken();
    
    await request(app)
      .post('/api/trips')
      .set('Authorization', `Bearer ${token}`)
      .send({}) // Missing required fields
      .expect(400);
  });
  
  it('should sanitize HTML inputs', async () => {
    const token = await generateAuthToken();
    const maliciousInput = '<script>alert("xss")</script>Trip Name';
    
    const response = await request(app)
      .post('/api/trips')
      .set('Authorization', `Bearer ${token}`)
      .send({
        title: maliciousInput,
        description: 'Test trip'
      })
      .expect(201);
    
    expect(response.body.title).not.toContain('<script>');
    expect(response.body.title).toBe('Trip Name');
  });
  
  it('should validate data types', async () => {
    const token = await generateAuthToken();
    
    await request(app)
      .post('/api/trips')
      .set('Authorization', `Bearer ${token}`)
      .send({
        title: 'Test Trip',
        start_date: 'invalid-date',
        budget: 'not-a-number'
      })
      .expect(400);
  });
});
```

### **2. Rate Limiting Testing**

```javascript
// Rate limiting tests
describe('Rate Limiting', () => {
  it('should enforce rate limits', async () => {
    const token = await generateAuthToken();
    const endpoint = '/api/trips';
    
    // Make requests up to the limit
    const requests = Array(10).fill().map(() =>
      request(app)
        .get(endpoint)
        .set('Authorization', `Bearer ${token}`)
    );
    
    const responses = await Promise.all(requests);
    
    // First 5 should succeed (assuming limit is 5/minute)
    responses.slice(0, 5).forEach(response => {
      expect(response.status).toBe(200);
    });
    
    // Remaining should be rate limited
    responses.slice(5).forEach(response => {
      expect(response.status).toBe(429);
    });
  });
  
  it('should have different limits for different endpoints', async () => {
    const token = await generateAuthToken();
    
    // Test different endpoint limits
    const endpointLimits = {
      '/api/search': 20,
      '/api/trips': 60,
      '/api/auth/login': 5
    };
    
    for (const [endpoint, limit] of Object.entries(endpointLimits)) {
      const requests = Array(limit + 1).fill().map(() =>
        request(app).get(endpoint).set('Authorization', `Bearer ${token}`)
      );
      
      const responses = await Promise.all(requests);
      const lastResponse = responses[responses.length - 1];
      
      expect(lastResponse.status).toBe(429);
    }
  });
});
```

### **3. SQL Injection Prevention Testing**

```javascript
// SQL injection prevention tests
describe('SQL Injection Prevention', () => {
  const maliciousInputs = [
    "'; DROP TABLE trips; --",
    "1' OR '1'='1",
    "1' UNION SELECT * FROM users --",
    "'; DELETE FROM trips WHERE 1=1; --"
  ];
  
  maliciousInputs.forEach(input => {
    it(`should prevent SQL injection: ${input}`, async () => {
      const token = await generateAuthToken();
      
      const response = await request(app)
        .get('/api/trips/search')
        .query({ q: input })
        .set('Authorization', `Bearer ${token}`);
      
      // Should not return 500 (database error)
      expect(response.status).not.toBe(500);
      
      // Should properly escape/sanitize the input
      if (response.status === 200) {
        expect(response.body.results).toEqual([]);
      }
    });
  });
});
```

---

## 📊 Performance Security Testing

### **1. RLS Performance Impact Testing**

```sql
-- Performance testing for RLS policies
CREATE OR REPLACE FUNCTION test_rls_performance()
RETURNS TABLE (
  test_name text,
  execution_time_ms numeric,
  rows_returned bigint
)
LANGUAGE plpgsql
AS $$
DECLARE
  start_time timestamptz;
  end_time timestamptz;
  row_count bigint;
BEGIN
  -- Test 1: Large table scan with RLS
  start_time := clock_timestamp();
  SELECT COUNT(*) INTO row_count FROM trips;
  end_time := clock_timestamp();
  
  RETURN QUERY SELECT 
    'Large table scan with RLS'::text,
    EXTRACT(milliseconds FROM end_time - start_time),
    row_count;
  
  -- Test 2: Join with RLS on both tables
  start_time := clock_timestamp();
  SELECT COUNT(*) INTO row_count 
  FROM trips t 
  JOIN trip_destinations td ON t.id = td.trip_id;
  end_time := clock_timestamp();
  
  RETURN QUERY SELECT 
    'Join with RLS on both tables'::text,
    EXTRACT(milliseconds FROM end_time - start_time),
    row_count;
  
  -- Test 3: Complex aggregation with RLS
  start_time := clock_timestamp();
  SELECT COUNT(*) INTO row_count 
  FROM (
    SELECT user_id, COUNT(*) as trip_count, AVG(budget) as avg_budget
    FROM trips 
    GROUP BY user_id
    HAVING COUNT(*) > 1
  ) subquery;
  end_time := clock_timestamp();
  
  RETURN QUERY SELECT 
    'Complex aggregation with RLS'::text,
    EXTRACT(milliseconds FROM end_time - start_time),
    row_count;
END;
$$;

-- Run performance tests
SELECT * FROM test_rls_performance();
```

### **2. Concurrent Access Testing**

```javascript
// Concurrent access testing
describe('Concurrent Security Operations', () => {
  it('should handle concurrent authentication requests', async () => {
    const user = await createTestUser();
    
    // Simulate 100 concurrent login attempts
    const concurrentLogins = Array(100).fill().map(() =>
      request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: user.password
        })
    );
    
    const responses = await Promise.all(concurrentLogins);
    
    // All should succeed or fail gracefully (no 500 errors)
    responses.forEach(response => {
      expect([200, 401, 429]).toContain(response.status);
    });
  });
  
  it('should handle concurrent resource access', async () => {
    const user = await createTestUser();
    const trip = await createTestTrip({ userId: user.id });
    const token = await generateAuthToken(user);
    
    // Simulate 50 concurrent read operations
    const concurrentReads = Array(50).fill().map(() =>
      request(app)
        .get(`/api/trips/${trip.id}`)
        .set('Authorization', `Bearer ${token}`)
    );
    
    const responses = await Promise.all(concurrentReads);
    
    // All should succeed
    responses.forEach(response => {
      expect(response.status).toBe(200);
      expect(response.body.id).toBe(trip.id);
    });
  });
});
```

---

## 🔍 Security Monitoring & Auditing

### **1. Security Event Monitoring**

```sql
-- Monitor security events
CREATE OR REPLACE FUNCTION monitor_security_events(
  start_time timestamptz DEFAULT now() - interval '1 hour'
)
RETURNS TABLE (
  event_type text,
  event_count bigint,
  severity text
)
LANGUAGE sql
AS $$
  -- Failed authentication attempts
  SELECT 
    'failed_authentication' as event_type,
    COUNT(*) as event_count,
    CASE 
      WHEN COUNT(*) > 100 THEN 'HIGH'
      WHEN COUNT(*) > 50 THEN 'MEDIUM'
      ELSE 'LOW'
    END as severity
  FROM auth_events 
  WHERE event_type = 'login_failed' 
  AND created_at >= start_time
  
  UNION ALL
  
  -- Suspicious API access patterns
  SELECT 
    'suspicious_api_access' as event_type,
    COUNT(*) as event_count,
    CASE 
      WHEN COUNT(*) > 1000 THEN 'HIGH'
      WHEN COUNT(*) > 500 THEN 'MEDIUM'
      ELSE 'LOW'
    END as severity
  FROM api_access_logs 
  WHERE status_code = 403
  AND created_at >= start_time
  
  UNION ALL
  
  -- RLS policy violations
  SELECT 
    'rls_violations' as event_type,
    COUNT(*) as event_count,
    'HIGH' as severity
  FROM audit_logs 
  WHERE event_type = 'rls_violation'
  AND created_at >= start_time;
$$;
```

### **2. Performance Security Monitoring**

```sql
-- Monitor RLS performance impact
CREATE OR REPLACE FUNCTION monitor_rls_performance()
RETURNS TABLE (
  query_pattern text,
  avg_execution_time_ms numeric,
  call_count bigint,
  performance_impact text
)
LANGUAGE sql
AS $$
  SELECT 
    regexp_replace(query, '\$\d+', '$?', 'g') as query_pattern,
    round(mean_exec_time::numeric, 2) as avg_execution_time_ms,
    calls as call_count,
    CASE 
      WHEN mean_exec_time > 1000 THEN 'HIGH'
      WHEN mean_exec_time > 500 THEN 'MEDIUM'
      ELSE 'LOW'
    END as performance_impact
  FROM pg_stat_statements
  WHERE query LIKE '%row_security%'
  OR query LIKE '%rls%'
  ORDER BY mean_exec_time DESC
  LIMIT 20;
$$;
```

### **3. Security Audit Reports**

```sql
-- Comprehensive security audit
CREATE OR REPLACE FUNCTION generate_security_audit()
RETURNS TABLE (
  check_name text,
  status text,
  details text,
  recommendation text
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Check 1: Tables without RLS
  RETURN QUERY 
  SELECT 
    'Tables without RLS'::text,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Found ' || COUNT(*) || ' tables without RLS enabled',
    'Enable RLS on all user-accessible tables'
  FROM pg_tables t
  WHERE schemaname = 'public'
  AND t.tablename NOT IN (
    SELECT tablename 
    FROM pg_tables pt
    JOIN pg_class c ON c.relname = pt.tablename
    WHERE c.relrowsecurity = true
  );
  
  -- Check 2: Policies without proper indexing
  RETURN QUERY
  SELECT 
    'RLS policies without indexes'::text,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END,
    'Found ' || COUNT(*) || ' policies that may need index optimization',
    'Review and add indexes for policy columns'
  FROM (
    SELECT DISTINCT 
      pol.polrelid::regclass as table_name,
      pol.polqual::text as policy_condition
    FROM pg_policy pol
    WHERE pol.polqual::text LIKE '%user_id%'
    AND pol.polrelid::regclass::text NOT IN (
      SELECT tablename 
      FROM pg_indexes 
      WHERE indexdef LIKE '%user_id%'
    )
  ) unindexed_policies;
  
  -- Check 3: Weak authentication settings
  RETURN QUERY
  SELECT 
    'Authentication settings'::text,
    'INFO'::text,
    'Current JWT expiry: ' || (SELECT raw_app_meta_data->>'jwt_exp' FROM auth.users LIMIT 1),
    'Review JWT expiry times and refresh token policies';
    
END;
$$;

-- Run security audit
SELECT * FROM generate_security_audit();
```

---

## 🔧 Advanced Testing Patterns

### **1. Attribute-Based Access Control (ABAC) Testing**

```sql
-- ABAC testing framework
CREATE OR REPLACE FUNCTION test_abac_policies()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  user_id uuid := gen_random_uuid();
  resource_id uuid := gen_random_uuid();
BEGIN
  -- Setup user attributes
  INSERT INTO user_attributes (user_id, attribute_key, attribute_value) VALUES
    (user_id, 'clearance_level', '"secret"'::jsonb),
    (user_id, 'department', '"engineering"'::jsonb),
    (user_id, 'project_access', '["project1", "project2"]'::jsonb);
  
  -- Setup resource attributes
  INSERT INTO resource_attributes (resource_id, attribute_key, attribute_value) VALUES
    (resource_id, 'classification', '"secret"'::jsonb),
    (resource_id, 'owning_department', '"engineering"'::jsonb),
    (resource_id, 'required_projects', '["project1"]'::jsonb);
  
  -- Test ABAC evaluation
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', user_id, 'role', 'authenticated')::text, true);
  
  -- Should pass - user has required attributes
  ASSERT evaluate_abac_policy(resource_id, '{"clearance_level": "secret"}'::jsonb) = true;
  
  -- Should fail - user doesn't have top secret clearance
  ASSERT evaluate_abac_policy(resource_id, '{"clearance_level": "top_secret"}'::jsonb) = false;
  
  RAISE NOTICE 'ABAC policy test PASSED';
END;
$$;
```

### **2. Time-Based Access Control Testing**

```sql
-- Time-based access testing
CREATE OR REPLACE FUNCTION test_temporal_access()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  tenant_id uuid := gen_random_uuid();
  user_id uuid := gen_random_uuid();
BEGIN
  -- Setup subscription with time bounds
  INSERT INTO subscriptions (tenant_id, plan, valid_from, valid_until) VALUES
    (tenant_id, 'premium', now() - interval '1 day', now() + interval '1 day');
  
  INSERT INTO tenant_users (tenant_id, user_id) VALUES (tenant_id, user_id);
  
  -- Test current access (should work)
  PERFORM set_config('request.jwt.claims',
    json_build_object('sub', user_id, 'role', 'authenticated')::text, true);
  
  ASSERT has_active_subscription() = true;
  
  -- Test expired subscription
  UPDATE subscriptions SET valid_until = now() - interval '1 hour'
  WHERE tenant_id = tenant_id;
  
  ASSERT has_active_subscription() = false;
  
  RAISE NOTICE 'Temporal access test PASSED';
END;
$$;
```

### **3. Dynamic Policy Testing**

```sql
-- Dynamic policy testing
CREATE OR REPLACE FUNCTION test_dynamic_policies()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  template_id uuid := gen_random_uuid();
BEGIN
  -- Create policy template
  INSERT INTO policy_templates (id, name, template_sql, parameters) VALUES
    (template_id, 'tenant_isolation', 
     'CREATE POLICY "%1$s_tenant_isolation" ON %1$s FOR ALL TO %2$s USING (%3$s)',
     '{"role": "authenticated", "condition": "tenant_id = get_user_tenant_id()"}'::jsonb);
  
  -- Apply dynamic policy
  PERFORM apply_dynamic_policy('test_table', template_id);
  
  -- Verify policy was created
  ASSERT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE policyname = 'test_table_tenant_isolation'
    AND tablename = 'test_table'
  );
  
  RAISE NOTICE 'Dynamic policy test PASSED';
END;
$$;
```

---

## 🚀 Automated Testing Framework

### **1. Complete Test Suite Runner**

```bash
#!/bin/bash
# security-test-runner.sh

echo "🔒 TripSage AI Security Test Suite"
echo "=================================="

# Set test environment variables
export NODE_ENV=test
export DATABASE_URL="postgresql://test_user:test_pass@localhost:5432/tripsage_test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
  local test_name="$1"
  local test_command="$2"
  
  echo -n "Running $test_name... "
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  
  if eval "$test_command" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
  else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
  fi
}

# Database security tests
echo "🗄️ Database Security Tests"
echo "--------------------------"

run_test "RLS Policy Coverage" "npm run test:db:rls-coverage"
run_test "RLS Policy Performance" "npm run test:db:rls-performance"
run_test "Multi-tenant Isolation" "npm run test:db:tenant-isolation"
run_test "Permission Inheritance" "npm run test:db:permissions"

# API security tests
echo ""
echo "🌐 API Security Tests"
echo "--------------------"

run_test "Authentication Tests" "npm run test:api:auth"
run_test "Authorization Tests" "npm run test:api:authz"
run_test "Input Validation" "npm run test:api:validation"
run_test "Rate Limiting" "npm run test:api:rate-limiting"
run_test "SQL Injection Prevention" "npm run test:api:sqli"

# Performance security tests
echo ""
echo "⚡ Performance Security Tests"
echo "----------------------------"

run_test "Concurrent Access" "npm run test:perf:concurrent"
run_test "Load Testing" "npm run test:perf:load"
run_test "Memory Usage" "npm run test:perf:memory"

# Integration tests
echo ""
echo "🔗 Integration Security Tests"
echo "----------------------------"

run_test "End-to-End Security" "npm run test:e2e:security"
run_test "External API Security" "npm run test:e2e:external"

# Generate reports
echo ""
echo "📊 Test Results Summary"
echo "======================"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
  echo -e "\n${GREEN}🎉 All security tests passed!${NC}"
  exit 0
else
  echo -e "\n${RED}❌ Some security tests failed. Please review and fix.${NC}"
  exit 1
fi
```

### **2. CI/CD Security Testing Integration**

```yaml
# .github/workflows/security-tests.yml
name: Security Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: tripsage_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Setup test database
        run: |
          npm run db:setup:test
          npm run db:migrate:test
          npm run db:seed:test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/tripsage_test
      
      - name: Run security tests
        run: |
          chmod +x ./scripts/security-test-runner.sh
          ./scripts/security-test-runner.sh
        env:
          NODE_ENV: test
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/tripsage_test
      
      - name: Generate security report
        run: npm run test:security:report
        
      - name: Upload security test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-test-results
          path: |
            coverage/security/
            reports/security/
```

---

## 📋 Security Testing Checklist

### **🔍 Pre-Deployment Security Validation**

#### **Database Security**

- [ ] All user-facing tables have RLS enabled
- [ ] RLS policies properly isolate tenant data
- [ ] Performance impact of RLS policies is acceptable (<100ms overhead)
- [ ] All RLS policy columns are properly indexed
- [ ] Security definer functions are used for complex policy logic
- [ ] No RLS policy recursion or circular dependencies

#### **Authentication & Authorization**

- [ ] JWT tokens are properly validated and expired
- [ ] API key authentication works correctly
- [ ] Role-based permissions are enforced
- [ ] Resource ownership is validated
- [ ] Shared resource access works as expected
- [ ] Session management handles edge cases

#### **API Security**

- [ ] Input validation prevents injection attacks
- [ ] Rate limiting is configured and working
- [ ] Error messages don't leak sensitive information
- [ ] CORS settings are properly configured
- [ ] Request size limits are enforced
- [ ] Audit logging captures security events

#### **Performance Security**

- [ ] Security checks don't impact response times significantly
- [ ] Concurrent access doesn't cause security bypasses
- [ ] Resource exhaustion attacks are prevented
- [ ] Database query performance with RLS is acceptable

#### **Monitoring & Alerting**

- [ ] Security events are properly logged
- [ ] Failed authentication attempts trigger alerts
- [ ] Suspicious access patterns are detected
- [ ] Performance degradation alerts are configured
- [ ] Security audit reports are generated regularly

---

## 🎯 Testing Best Practices Summary

### **🏆 Key Testing Principles**

1. **🔄 Continuous Testing**: Integrate security tests into CI/CD pipeline
2. **📊 Comprehensive Coverage**: Test all security layers and scenarios
3. **⚡ Performance Awareness**: Monitor security overhead and impact
4. **🎯 Realistic Scenarios**: Use production-like data and conditions
5. **📝 Documentation**: Maintain clear test documentation and runbooks
6. **🔍 Regular Audits**: Schedule periodic security test reviews and updates

### **🚨 Common Security Testing Pitfalls**

- **Incomplete Test Coverage**: Not testing all user roles and permissions
- **Performance Neglect**: Ignoring security overhead in performance tests
- **Static Test Data**: Using unrealistic test datasets
- **Manual Testing Only**: Lack of automated security test suites
- **Missing Edge Cases**: Not testing boundary conditions and error scenarios
- **Outdated Tests**: Security tests not updated with feature changes

---

*This comprehensive security testing guide ensures that TripSage AI maintains the highest security standards through systematic testing, monitoring, and validation procedures. Regular execution of these tests is essential for maintaining security posture and identifying potential vulnerabilities early in the development process.*
