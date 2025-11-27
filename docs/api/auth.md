# Auth

Authentication endpoints for user login and session management.

## `POST /api/auth/login`

Email/password login; sets Supabase authentication cookies.

**Authentication**: Anonymous  
**Rate Limit Key**: Not rate-limited

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User email address |
| `password` | string | Yes | User password (min 8 chars) |
| `rememberMe` | boolean | No | Remember session |

### Response

`200 OK`

```json
{
  "accessToken": "eyJ...",
  "expiresIn": 3600,
  "refreshToken": "refresh_...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe"
  }
}
```

### Errors

- `400` - Invalid email or password format
- `401` - Invalid credentials

### Examples

#### cURL

```bash
curl -X POST "http://localhost:3000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

#### TypeScript

```typescript
const response = await fetch("http://localhost:3000/api/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "user@example.com",
    password: "securepass123",
  }),
});
const { accessToken, user } = await response.json();
```

#### Python

```python
import requests

response = requests.post(
    "http://localhost:3000/api/auth/login",
    json={"email": "user@example.com", "password": "securepass123"}
)
data = response.json()
```
