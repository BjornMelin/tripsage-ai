# 🔑 TripSage API Key Management Service

> **Comprehensive API Key Service Reference**  
> BYOK (Bring Your Own Key) functionality, validation, rotation, and monitoring for TripSage developers

## 📋 Table of Contents

- [Overview](#overview)
- [API Key Management](#api-key-management)
- [Validation & Monitoring](#validation--monitoring)
- [Security Features](#security-features)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

The TripSage API Key Management Service provides comprehensive BYOK (Bring Your Own Key) functionality, allowing users to securely store, validate, and manage third-party API keys for external service integrations.

### Key Features

- **🔐 Secure Storage**: Encrypted API key storage with user isolation
- **✅ Real-time Validation**: Automatic validation against external services
- **🔄 Key Rotation**: Safe key rotation with validation
- **📊 Monitoring**: Usage tracking and health metrics
- **🛡️ Security**: Audit logging and access controls

### Supported Services

| Service | Validation Method | Key Format |
|---------|------------------|------------|
| OpenAI | API call to `/models` | `sk-...` |
| Anthropic | API call to `/models` | `sk-ant-...` |
| Google | Vertex AI validation | `AIza...` |
| Azure | OpenAI compatibility | Custom |

---

## API Key Management

### Base Endpoint

All API key operations are available under:

```
/api/keys
```

**Authentication Required**: JWT Bearer token

### List API Keys

Retrieve all API keys for the authenticated user.

```http
GET /api/keys
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**

```json
{
  "api_keys": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "OpenAI Production Key",
      "service": "openai",
      "description": "Primary OpenAI key for chat completions",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "expires_at": "2026-01-15T10:30:00Z",
      "is_valid": true,
      "last_used": "2025-01-15T12:00:00Z"
    }
  ],
  "count": 1
}
```

### Create API Key

Add a new API key with automatic validation.

```http
POST /api/keys
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "OpenAI Production Key",
  "service": "openai",
  "key": "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
  "description": "Primary OpenAI key for chat completions",
  "expires_at": "2026-01-15T10:30:00Z"
}
```

**Response (201 Created):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "OpenAI Production Key",
  "service": "openai",
  "description": "Primary OpenAI key for chat completions",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "expires_at": "2026-01-15T10:30:00Z",
  "is_valid": true,
  "last_used": null
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Invalid API key for openai: Authentication failed"
}
```

### Validate API Key

Test an API key without storing it.

```http
POST /api/keys/validate
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "key": "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
  "service": "openai"
}
```

**Response (200 OK):**

```json
{
  "is_valid": true,
  "service": "openai",
  "message": "API key validated successfully"
}
```

**Response (200 OK - Invalid Key):**

```json
{
  "is_valid": false,
  "service": "openai",
  "message": "Authentication failed: Invalid API key"
}
```

### Rotate API Key

Update an existing API key with a new value.

```http
POST /api/keys/{key_id}/rotate
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "new_key": "sk-new1234567890abcdef1234567890abcdef1234567890abcdef"
}
```

**Response (200 OK):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "OpenAI Production Key",
  "service": "openai",
  "description": "Primary OpenAI key for chat completions",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T16:45:00Z",
  "expires_at": "2026-01-15T10:30:00Z",
  "is_valid": true,
  "last_used": null
}
```

### Delete API Key

Remove an API key permanently.

```http
DELETE /api/keys/{key_id}
Authorization: Bearer {jwt_token}
```

**Response (204 No Content)**

**Error Response (404 Not Found):**

```json
{
  "detail": "API key not found"
}
```

**Error Response (403 Forbidden):**

```json
{
  "detail": "You do not have permission to delete this API key"
}
```

---

## Validation & Monitoring

### Key Health Metrics

Get system-wide API key health metrics (admin access required).

```http
GET /api/keys/metrics
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**

```json
{
  "total_keys": 1247,
  "valid_keys": 1198,
  "invalid_keys": 49,
  "services": {
    "openai": {
      "total": 856,
      "valid": 823,
      "invalid": 33
    },
    "anthropic": {
      "total": 391,
      "valid": 375,
      "invalid": 16
    }
  },
  "last_validation_run": "2025-01-15T12:00:00Z"
}
```

### Audit Log

Get audit trail for API key operations.

```http
GET /api/keys/audit?limit=50
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**

```json
[
  {
    "timestamp": "2025-01-15T12:00:00Z",
    "action": "key_created",
    "key_id": "123e4567-e89b-12d3-a456-426614174000",
    "service": "openai",
    "user_id": "user_123",
    "ip_address": "192.168.1.100",
    "user_agent": "TripSage-Client/1.0"
  },
  {
    "timestamp": "2025-01-15T11:45:00Z",
    "action": "key_validated",
    "key_id": "123e4567-e89b-12d3-a456-426614174000",
    "service": "openai",
    "result": "valid",
    "response_time_ms": 145
  }
]
```

---

## Security Features

### Authentication Integration

API key operations require valid JWT authentication:

```mermaid
graph LR
    A[Client Request] --> B[JWT Validation]
    B --> C[Principal Extraction]
    C --> D[User ID Check]
    D --> E[Resource Access Control]
    E --> F[API Key Operation]
    F --> G[Audit Logging]
```

### Access Control

- **User Isolation**: Users can only access their own API keys
- **Principal Validation**: JWT tokens validated on every request
- **Resource Ownership**: Key ownership verified before operations
- **Audit Trail**: All operations logged for security monitoring

### Data Protection

```python
# Example of secure key handling
async def create_key(user_id: str, key_data: ApiKeyCreate):
    # 1. Validate key with external service
    validation = await validate_external_key(key_data.key, key_data.service)
    
    # 2. Encrypt key before storage
    encrypted_key = encrypt_key(key_data.key)
    
    # 3. Store with user association
    stored_key = await store_key(user_id, encrypted_key, key_data)
    
    # 4. Log creation event
    await audit_log("key_created", stored_key.id, user_id)
    
    return stored_key
```

---

## Integration Examples

### Python Client

```python
import httpx
from typing import Dict, List, Optional

class TripSageAPIKeyClient:
    def __init__(self, jwt_token: str, base_url: str = "https://api.tripsage.ai"):
        self.jwt_token = jwt_token
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {jwt_token}"}
    
    async def create_api_key(
        self, 
        name: str, 
        service: str, 
        key: str,
        description: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> Dict:
        """Create a new API key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/keys",
                headers=self.headers,
                json={
                    "name": name,
                    "service": service,
                    "key": key,
                    "description": description,
                    "expires_at": expires_at
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_api_keys(self) -> List[Dict]:
        """List all API keys for the user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/keys",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()["api_keys"]
    
    async def validate_key(self, key: str, service: str) -> Dict:
        """Validate an API key without storing it."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/keys/validate",
                headers=self.headers,
                json={"key": key, "service": service}
            )
            response.raise_for_status()
            return response.json()
    
    async def rotate_key(self, key_id: str, new_key: str) -> Dict:
        """Rotate an existing API key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/keys/{key_id}/rotate",
                headers=self.headers,
                json={"new_key": new_key}
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_key(self, key_id: str) -> None:
        """Delete an API key."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/keys/{key_id}",
                headers=self.headers
            )
            response.raise_for_status()

# Usage example
async def main():
    client = TripSageAPIKeyClient("your-jwt-token")
    
    # Validate a key before storing
    validation = await client.validate_key(
        "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
        "openai"
    )
    
    if validation["is_valid"]:
        # Create the key
        api_key = await client.create_api_key(
            name="My OpenAI Key",
            service="openai",
            key="sk-1234567890abcdef1234567890abcdef1234567890abcdef",
            description="Production OpenAI key for chat features"
        )
        print(f"Created API key: {api_key['id']}")
    else:
        print(f"Invalid key: {validation['message']}")
```

### TypeScript/JavaScript Client

```typescript
interface APIKey {
  id: string;
  name: string;
  service: string;
  description?: string;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  is_valid: boolean;
  last_used?: string;
}

interface ValidationResult {
  is_valid: boolean;
  service: string;
  message: string;
}

class TripSageAPIKeyClient {
  private jwtToken: string;
  private baseUrl: string;

  constructor(jwtToken: string, baseUrl: string = "https://api.tripsage.ai") {
    this.jwtToken = jwtToken;
    this.baseUrl = baseUrl;
  }

  private get headers() {
    return {
      "Authorization": `Bearer ${this.jwtToken}`,
      "Content-Type": "application/json"
    };
  }

  async createAPIKey(data: {
    name: string;
    service: string;
    key: string;
    description?: string;
    expires_at?: string;
  }): Promise<APIKey> {
    const response = await fetch(`${this.baseUrl}/api/keys`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create API key");
    }

    return response.json();
  }

  async listAPIKeys(): Promise<APIKey[]> {
    const response = await fetch(`${this.baseUrl}/api/keys`, {
      headers: this.headers
    });

    if (!response.ok) {
      throw new Error("Failed to list API keys");
    }

    const data = await response.json();
    return data.api_keys;
  }

  async validateKey(key: string, service: string): Promise<ValidationResult> {
    const response = await fetch(`${this.baseUrl}/api/keys/validate`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({ key, service })
    });

    if (!response.ok) {
      throw new Error("Failed to validate API key");
    }

    return response.json();
  }

  async rotateKey(keyId: string, newKey: string): Promise<APIKey> {
    const response = await fetch(`${this.baseUrl}/api/keys/${keyId}/rotate`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({ new_key: newKey })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to rotate API key");
    }

    return response.json();
  }

  async deleteKey(keyId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/keys/${keyId}`, {
      method: "DELETE",
      headers: this.headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to delete API key");
    }
  }
}

// Usage example
async function manageAPIKeys() {
  const client = new TripSageAPIKeyClient("your-jwt-token");

  try {
    // List existing keys
    const keys = await client.listAPIKeys();
    console.log("Existing keys:", keys);

    // Validate a new key
    const validation = await client.validateKey(
      "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
      "openai"
    );

    if (validation.is_valid) {
      // Create the key
      const newKey = await client.createAPIKey({
        name: "My OpenAI Key",
        service: "openai",
        key: "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
        description: "Production OpenAI key for chat features"
      });
      console.log("Created API key:", newKey.id);
    } else {
      console.error("Invalid key:", validation.message);
    }
  } catch (error) {
    console.error("Error managing API keys:", error);
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. API Key Validation Fails

**Symptoms:**
- 400 Bad Request when creating keys
- `is_valid: false` in validation responses

**Solutions:**
```python
# Check key format for each service
SERVICE_KEY_PATTERNS = {
    "openai": r"^sk-[a-zA-Z0-9]{48}$",
    "anthropic": r"^sk-ant-[a-zA-Z0-9]+$",
    "google": r"^AIza[a-zA-Z0-9_-]{35}$"
}

def validate_key_format(key: str, service: str) -> bool:
    pattern = SERVICE_KEY_PATTERNS.get(service)
    if not pattern:
        return False
    return bool(re.match(pattern, key))
```

#### 2. Permission Denied Errors

**Symptoms:**
- 403 Forbidden when accessing keys
- "You do not have permission" messages

**Solutions:**
- Verify JWT token is valid and not expired
- Ensure you're only accessing your own keys
- Check that the key ID exists and belongs to your user

#### 3. Service Validation Timeouts

**Symptoms:**
- Slow validation responses
- Timeout errors during key creation

**Solutions:**
```python
# Implement validation with timeout
async def validate_with_timeout(key: str, service: str, timeout: int = 10):
    try:
        async with asyncio.timeout(timeout):
            return await external_service_validate(key, service)
    except asyncio.TimeoutError:
        return ValidationResult(
            is_valid=False,
            service=service,
            message="Validation timeout - service may be unavailable"
        )
```

### Debug Mode

Enable detailed logging for API key operations:

```python
import logging

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("tripsage.api_keys")

# This will show validation steps, encryption operations, and audit events
```

### Testing Endpoints

```bash
# Test key validation
curl -X POST "https://api.tripsage.ai/api/keys/validate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key": "sk-test123", "service": "openai"}'

# Test key creation
curl -X POST "https://api.tripsage.ai/api/keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Key",
    "service": "openai",
    "key": "sk-test123",
    "description": "Testing key creation"
  }'

# List user keys
curl -X GET "https://api.tripsage.ai/api/keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Best Practices

### Security Guidelines

#### 1. Key Storage
```python
# ✅ Good: Store keys in environment variables
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ❌ Bad: Hardcode keys in source code
OPENAI_API_KEY = "sk-1234567890abcdef..."
```

#### 2. Key Rotation
```python
# Implement regular key rotation
async def rotate_keys_if_needed():
    keys = await client.list_api_keys()
    
    for key in keys:
        # Rotate keys older than 90 days
        if days_since_creation(key["created_at"]) > 90:
            new_key = generate_new_key_from_service(key["service"])
            await client.rotate_key(key["id"], new_key)
            logger.info(f"Rotated key {key['id']} for {key['service']}")
```

#### 3. Validation Before Storage
```python
# Always validate before creating
async def safe_key_creation(name: str, service: str, key: str):
    # 1. Validate format
    if not validate_key_format(key, service):
        raise ValueError(f"Invalid key format for {service}")
    
    # 2. Test with service
    validation = await client.validate_key(key, service)
    if not validation["is_valid"]:
        raise ValueError(f"Key validation failed: {validation['message']}")
    
    # 3. Create key
    return await client.create_api_key(name, service, key)
```

### Performance Tips

#### 1. Batch Operations
```python
# Validate multiple keys concurrently
async def validate_multiple_keys(keys: List[Dict]):
    tasks = []
    for key_data in keys:
        task = client.validate_key(key_data["key"], key_data["service"])
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### 2. Caching Validation Results
```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache validation results for short periods
validation_cache = {}

async def cached_validate_key(key: str, service: str):
    cache_key = f"{service}:{key[:10]}..."  # Don't cache full key
    
    if cache_key in validation_cache:
        cached_result, timestamp = validation_cache[cache_key]
        if datetime.now() - timestamp < timedelta(minutes=5):
            return cached_result
    
    result = await client.validate_key(key, service)
    validation_cache[cache_key] = (result, datetime.now())
    return result
```

#### 3. Error Handling Patterns
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def resilient_key_operation(operation_func, *args, **kwargs):
    """Retry key operations with exponential backoff."""
    try:
        return await operation_func(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in [500, 502, 503, 504]:
            # Retry on server errors
            raise
        else:
            # Don't retry on client errors
            raise e
```

---

## 🔗 Related Documentation

### Core References

- **[Authentication Guide](../api/authentication.md)** - JWT token management and auth flows
- **[REST API Endpoints](../api/rest-endpoints.md)** - Complete API reference
- **[Security Guide](../operators/security-guide.md)** - Production security best practices
- **[External Integrations](external-integrations.md)** - Third-party service integration patterns

### Development Guides

- **[API Development](api-development.md)** - Backend development with FastAPI
- **[Testing Guide](testing-guide.md)** - Testing API key functionality
- **[Debugging Guide](debugging-guide.md)** - Troubleshooting API key issues

### Common Workflows

- **New to API keys?** → Start with [Authentication Guide](../api/authentication.md#api-key-authentication)
- **Integrating services?** → Check [External Integrations](external-integrations.md)
- **Security concerns?** → Review [Security Guide](../operators/security-guide.md)
- **Testing integration?** → Use [Testing Guide](testing-guide.md#testing-api-keys)

---

*This documentation covers the complete API key management service functionality. For additional support or feature requests, refer to the main [Developer Documentation](README.md).*