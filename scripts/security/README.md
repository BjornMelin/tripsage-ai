# Security Scripts

Security validation, vulnerability testing, and audit scripts for maintaining system security.

## Overview

Security scripts help identify vulnerabilities, validate security policies, and ensure compliance with security requirements. These scripts are critical for:

- Pre-deployment security validation
- Regular security audits
- Vulnerability assessment
- Compliance reporting
- Incident response

## Scripts

### rls_vulnerability_tests.sql

Comprehensive Row Level Security (RLS) policy testing for PostgreSQL/Supabase.

**Purpose**: Validate that RLS policies correctly enforce access controls and prevent unauthorized data access.

**Tests Include**:

- User isolation (users can't see each other's data)
- Role-based access control
- Policy bypass attempts
- Edge cases and boundary conditions
- Performance impact of policies

**Usage**:

```bash
# Run all RLS tests
psql $DATABASE_URL -f scripts/security/rls_vulnerability_tests.sql

# Run specific test suite
psql $DATABASE_URL -c "SELECT test_user_isolation();"

# Generate detailed report
psql $DATABASE_URL -f scripts/security/rls_vulnerability_tests.sql \
  -o rls_audit_report.txt
```

**Example Test Cases**:

```sql
-- Test: Users cannot access other users' trips
-- Expected: 0 rows returned
SET LOCAL auth.uid = 'user-1-uuid';
SELECT COUNT(*) FROM trips WHERE user_id = 'user-2-uuid';

-- Test: Admin role can access all trips
-- Expected: All rows returned
SET LOCAL auth.role = 'admin';
SELECT COUNT(*) FROM trips;
```

### security_validation.py (root level)

Comprehensive security audit script that validates multiple security aspects.

**Checks**:

- Database security configurations
- API endpoint security
- Authentication/authorization flows
- Encryption status
- Audit logging
- Vulnerability scanning

**Usage**:

```bash
# Run full security audit
python scripts/security_validation.py

# Check specific components
python scripts/security_validation.py --components database,api

# Generate compliance report
python scripts/security_validation.py --compliance-report

# Output in different formats
python scripts/security_validation.py --output-format json
```

## Security Test Categories

### 1. Access Control Testing

**Row Level Security (RLS)**:

- User data isolation
- Role-based permissions
- Policy effectiveness
- Bypass attempts

**API Security**:

- Authentication requirements
- Authorization checks
- Rate limiting
- Input validation

### 2. Data Protection

**Encryption**:

- Data at rest encryption
- Data in transit (TLS/SSL)
- Key management
- Sensitive data masking

**Data Integrity**:

- Constraint validation
- Referential integrity
- Audit trail completeness

### 3. Vulnerability Assessment

**SQL Injection**:

```sql
-- Test parameterized queries
SELECT test_sql_injection_protection();

-- Check for dynamic SQL usage
SELECT find_dynamic_sql_usage();
```

**Authentication Weaknesses**:

- Password policy enforcement
- Session management
- Multi-factor authentication
- Brute force protection

### 4. Compliance Validation

**GDPR Compliance**:

- Data retention policies
- Right to deletion
- Data portability
- Consent management

**Security Headers**:

- CORS configuration
- CSP headers
- X-Frame-Options
- HSTS status

## Running Security Tests

### Pre-Deployment Checklist

```bash
#!/bin/bash
# security_check.sh

echo "🔒 Running Security Validation Suite"

# 1. Database Security
echo "Checking database security..."
psql $DATABASE_URL -f scripts/security/rls_vulnerability_tests.sql

# 2. API Security
echo "Validating API security..."
python scripts/security_validation.py --components api

# 3. Infrastructure Security
echo "Checking infrastructure security..."
python scripts/security_validation.py --components infrastructure

# 4. Generate Report
echo "Generating security report..."
python scripts/security_validation.py --compliance-report \
  --output-file security_report_$(date +%Y%m%d).html
```

### Continuous Security Monitoring

```yaml
# .github/workflows/security.yml
name: Security Audit

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'scripts/security/**'

jobs:
  security-audit:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Security Tests
        run: |
          python scripts/security_validation.py
          
      - name: Check for Vulnerabilities
        run: |
          # Run security scanners
          pip install safety bandit
          safety check
          bandit -r src/
          
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: security_report.html
```

## Security Best Practices

### 1. Regular Audits

Schedule regular security audits:

```bash
# Weekly comprehensive audit
0 0 * * 0 /app/scripts/security/weekly_audit.sh

# Daily quick checks
0 2 * * * /app/scripts/security/daily_checks.sh

# Real-time monitoring
*/5 * * * * /app/scripts/security/monitor_suspicious.sh
```

### 2. Incident Response

When security issues are detected:

1. **Immediate Actions**:

   ```bash
   # Block suspicious activity
   python scripts/security/block_suspicious_ips.py
   
   # Revoke compromised tokens
   python scripts/security/revoke_tokens.py --user-id <id>
   
   # Enable enhanced logging
   python scripts/security/enable_audit_mode.py
   ```

2. **Investigation**:

   ```bash
   # Analyze audit logs
   python scripts/security/analyze_audit_logs.py --timeframe 24h
   
   # Check for data exfiltration
   python scripts/security/check_data_access.py --suspicious
   ```

3. **Remediation**:

   ```bash
   # Apply security patches
   python scripts/security/apply_patches.py
   
   # Update security policies
   python scripts/security/update_policies.py
   ```

### 3. Preventive Measures

**Code Security**:

```python
# Example: Secure query execution
def get_user_data(user_id: str):
    # ✅ Good: Parameterized query
    query = "SELECT * FROM users WHERE id = $1"
    return db.execute(query, user_id)
    
    # ❌ Bad: String concatenation
    # query = f"SELECT * FROM users WHERE id = '{user_id}'"
```

**Configuration Security**:

```python
# Example: Secure configuration
SECURITY_CONFIG = {
    'session_timeout': 3600,  # 1 hour
    'max_login_attempts': 5,
    'password_min_length': 12,
    'require_mfa': True,
    'encryption_algorithm': 'AES-256-GCM',
}
```

## Writing Security Tests

### SQL Security Test Template

```sql
-- Security Test: [Test Name]
-- Purpose: [What this test validates]
-- Expected Result: [What indicates a pass]

CREATE OR REPLACE FUNCTION test_security_feature()
RETURNS TABLE(
    test_name TEXT,
    passed BOOLEAN,
    details TEXT
) AS $$
BEGIN
    -- Setup test data
    INSERT INTO test_users (id, email) VALUES 
        ('test-user-1', 'user1@test.com'),
        ('test-user-2', 'user2@test.com');
    
    -- Test 1: Positive case
    RETURN QUERY
    SELECT 
        'User can access own data'::TEXT,
        (SELECT COUNT(*) FROM user_data WHERE user_id = 'test-user-1') > 0,
        'User should see their own records'::TEXT;
    
    -- Test 2: Negative case
    RETURN QUERY
    SELECT 
        'User cannot access others data'::TEXT,
        (SELECT COUNT(*) FROM user_data WHERE user_id = 'test-user-2') = 0,
        'User should not see other users records'::TEXT;
    
    -- Cleanup
    DELETE FROM test_users WHERE id LIKE 'test-user-%';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Python Security Test Template

```python
#!/usr/bin/env python3
"""
Security test for [component].

Tests:
- Test 1 description
- Test 2 description
"""

import asyncio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SecurityTest:
    def __init__(self, config: Dict):
        self.config = config
        self.results = []
        
    async def test_authentication(self) -> Dict:
        """Test authentication security."""
        try:
            # Test invalid credentials
            result = await self.attempt_login("invalid", "invalid")
            assert result.status_code == 401, "Invalid login should fail"
            
            # Test rate limiting
            for _ in range(10):
                await self.attempt_login("test", "wrong")
            result = await self.attempt_login("test", "correct")
            assert result.status_code == 429, "Should be rate limited"
            
            return {"passed": True, "details": "Authentication secure"}
        except AssertionError as e:
            return {"passed": False, "details": str(e)}
            
    async def test_authorization(self) -> Dict:
        """Test authorization controls."""
        # Implementation here
        pass
        
    async def run_all_tests(self) -> List[Dict]:
        """Run all security tests."""
        tests = [
            self.test_authentication(),
            self.test_authorization(),
            # Add more tests
        ]
        
        results = await asyncio.gather(*tests)
        return results
        
    def generate_report(self):
        """Generate security audit report."""
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        
        print(f"Security Audit Report")
        print(f"====================")
        print(f"Passed: {passed}/{total}")
        print()
        
        for test in self.results:
            status = "✅" if test['passed'] else "❌"
            print(f"{status} {test['name']}: {test['details']}")

def main():
    # Test configuration
    config = {
        'api_url': 'https://api.example.com',
        'test_user': 'security_test_user',
    }
    
    tester = SecurityTest(config)
    results = asyncio.run(tester.run_all_tests())
    tester.results = results
    tester.generate_report()

if __name__ == '__main__':
    main()
```

## Security Metrics

### Key Security Indicators

1. **Vulnerability Count**:
   - Critical: 0 (must fix immediately)
   - High: 0 (fix within 24 hours)
   - Medium: < 5 (fix within week)
   - Low: Track and prioritize

2. **Policy Coverage**:
   - RLS policies: 100% of sensitive tables
   - API authentication: 100% of endpoints
   - Audit logging: 100% of write operations

3. **Compliance Score**:
   - GDPR: 95%+
   - SOC2: 90%+
   - HIPAA: As required

4. **Response Times**:
   - Incident detection: < 5 minutes
   - Initial response: < 15 minutes
   - Resolution: < 4 hours for critical

## Related Documentation

- [Security Best Practices](../../docs/security/best-practices.md)
- [Incident Response Plan](../../docs/security/incident-response.md)
- [Compliance Guide](../../docs/security/compliance.md)
- [Penetration Testing Guide](../../docs/security/pentest.md)
