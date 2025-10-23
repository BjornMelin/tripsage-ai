# Authentication

TripSage authentication methods and security practices.

## Authentication Methods

TripSage supports multiple authentication approaches:

| Method | Use Case | Security | Expiration |
|--------|----------|----------|------------|
| JWT Tokens | User apps | High | 1 hour (access), 30 days (refresh) |
| API Keys | Server-to-server | High | Configurable (up to 1 year) |
| OAuth 2.0 | Third-party integrations | High | Provider-specific |

## JWT Authentication

### User Login Flow

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'

# Login to get JWT
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'

# Use JWT token
curl http://localhost:8000/api/trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Token Management

- **Access tokens**: Short-lived (1 hour), used for API requests
- **Refresh tokens**: Long-lived (30 days), used to get new access tokens
- **Automatic refresh**: Implement in your client application

## API Key Authentication (BYOK)

### Bring Your Own Keys

Store and manage third-party API keys securely:

```bash
# Add API key
curl -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Duffel API Key",
    "service": "duffel",
    "key": "duffel_test_your_api_key_here"
  }'

# Use API key
curl http://localhost:8000/api/flights/search \
  -H "X-API-Key: YOUR_STORED_API_KEY"
```

### Supported Services

- **duffel**: Flight search and booking
- **google_maps**: Maps and location services  
- **openweather**: Weather information

## Security Best Practices

### Token Security

- Store tokens securely (httpOnly cookies, secure storage)
- Implement automatic token refresh
- Validate tokens on each request
- Use HTTPS in production

### API Key Management

- Rotate keys regularly
- Use descriptive names for organization
- Set appropriate expiration dates
- Monitor usage patterns

### Rate Limiting

Default limits (requests per minute):

- Unauthenticated: 10
- JWT tokens: 100
- API keys: 200-1000 (based on tier)

## Implementation Examples

### Frontend (React/Next.js)

```typescript
// JWT authentication
const login = async (email: string, password: string) => {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const { access_token } = await response.json();
  localStorage.setItem('token', access_token);
};

// API requests with auth
const apiRequest = async (url: string, options = {}) => {
  const token = localStorage.getItem('token');
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
};
```

### Backend (Python)

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    # Validate JWT token and return user
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY)
        return payload['sub']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Common Issues

### Token Expired

```json
{
  "error": true,
  "message": "Token has expired",
  "code": "TOKEN_EXPIRED"
}
```

**Solution**: Use refresh token to get new access token

### Invalid API Key

```json
{
  "error": true,
  "message": "API key not found",
  "code": "API_KEY_NOT_FOUND"
}
```

**Solution**: Verify API key is stored and valid

### Rate Limited

```json
{
  "error": true,
  "message": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED"
}
```

**Solution**: Implement exponential backoff and respect rate limits

## Next Steps

- **Interactive API docs**: Visit `http://localhost:8000/docs` for complete endpoint reference
- **Code examples**: Check `docs/api/usage-examples.md` for implementation samples
- **Error handling**: See `docs/api/error-codes.md` for detailed error information
