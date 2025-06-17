# 🔌 TripSage API Documentation

> **Build on TripSage Platform**  
> Complete API reference for developers integrating with TripSage's travel planning services

## 🚀 Quick Start

### Getting Your API Key

1. **Sign up** at [app.tripsage.ai](https://app.tripsage.ai)
2. Navigate to **Settings → API Keys**
3. Click **"Generate New Key"**
4. Copy and secure your key

### Your First API Call

```bash
curl https://api.tripsage.ai/v1/health \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 📚 API Documentation

### Core References

| Document | Description | Type |
|----------|-------------|------|
| **[Usage Examples](usage-examples.md)** | Practical code examples | 🔧 Tutorial |
| **[REST API Reference](../06_API_REFERENCE/REST_API_ENDPOINTS.md)** | Complete endpoint documentation | 📖 Reference |
| **[WebSocket API](../06_API_REFERENCE/WEBSOCKET_API.md)** | Real-time communication | 🔄 Reference |
| **[Authentication](../06_API_REFERENCE/AUTHENTICATION_API.md)** | Auth flows and security | 🔐 Reference |
| **[Data Models](../06_API_REFERENCE/DATA_MODELS.md)** | Request/response schemas | 📊 Reference |
| **[Error Codes](../06_API_REFERENCE/ERROR_CODES.md)** | Error handling guide | ⚠️ Reference |

### Integration Guides

- **[Getting Started](getting-started.md)** - First steps with the API
- **[SDK Installation](sdk-guide.md)** - Language-specific SDKs
- **[Webhooks](webhooks.md)** - Event subscriptions
- **[Rate Limits](rate-limits.md)** - Usage quotas and limits
- **[Best Practices](best-practices.md)** - Performance tips

## 🔧 Available SDKs

### Official SDKs

| Language | Package | Status | Install |
|----------|---------|---------|---------|
| **Python** | `tripsage-python` | ✅ Stable | `pip install tripsage` |
| **JavaScript** | `@tripsage/sdk` | ✅ Stable | `npm install @tripsage/sdk` |
| **TypeScript** | `@tripsage/sdk` | ✅ Stable | `npm install @tripsage/sdk` |
| **Go** | `tripsage-go` | 🚧 Beta | `go get github.com/tripsage/go-sdk` |
| **Ruby** | `tripsage-ruby` | 📅 Planned | Coming soon |

### Community SDKs

- **PHP**: [tripsage-php](https://github.com/community/tripsage-php)
- **Java**: [tripsage-java](https://github.com/community/tripsage-java)
- **C#**: [TripSage.NET](https://github.com/community/tripsage-dotnet)

## 🌐 API Endpoints Overview

### Core Services

#### Travel Planning

- `POST /v1/trips` - Create a new trip
- `GET /v1/trips/{id}` - Get trip details
- `PUT /v1/trips/{id}` - Update trip
- `DELETE /v1/trips/{id}` - Delete trip

#### Flight Search

- `POST /v1/flights/search` - Search flights
- `GET /v1/flights/{id}` - Get flight details
- `POST /v1/flights/book` - Book flight
- `POST /v1/flights/track` - Track prices

#### Accommodations

- `POST /v1/hotels/search` - Search hotels
- `GET /v1/hotels/{id}` - Get hotel details
- `POST /v1/hotels/book` - Book hotel
- `GET /v1/hotels/availability` - Check availability

#### AI Assistant

- `POST /v1/chat` - Send message to AI
- `GET /v1/chat/history` - Get conversation
- `POST /v1/chat/plan` - AI trip planning
- `WS /v1/chat/stream` - Real-time chat

## 💰 Pricing & Plans

### API Rate Limits by Plan

| Plan | Requests/Hour | Requests/Month | WebSocket | Support |
|------|---------------|----------------|-----------|----------|
| **Free** | 100 | 1,000 | ❌ | Community |
| **Developer** | 1,000 | 50,000 | ✅ 1 connection | Email |
| **Business** | 10,000 | 500,000 | ✅ 10 connections | Priority |
| **Enterprise** | Unlimited | Unlimited | ✅ Unlimited | Dedicated |

### Usage Monitoring

Track your API usage:

- Dashboard: [app.tripsage.ai/api/usage](https://app.tripsage.ai/api/usage)
- API: `GET /v1/usage`
- Headers: `X-RateLimit-*` in responses

## 🔐 Authentication

### API Key Authentication

```bash
curl https://api.tripsage.ai/v1/endpoint \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### OAuth 2.0 (User Context)

```bash
curl https://api.tripsage.ai/v1/user/trips \
  -H "Authorization: Bearer USER_ACCESS_TOKEN"
```

### JWT Tokens

For user-specific operations:

1. Obtain JWT via `/v1/auth/login`
2. Include in Authorization header
3. Refresh before expiration

## 🛠️ Development Tools

### API Explorer

Interactive API testing:

- Swagger UI: [api.tripsage.ai/docs](https://api.tripsage.ai/docs)
- GraphQL Playground: [api.tripsage.ai/graphql](https://api.tripsage.ai/graphql)
- Postman Collection: [Download](https://api.tripsage.ai/postman)

### Testing Environment

Sandbox for development:

- Base URL: `https://sandbox.tripsage.ai/v1`
- Test API Key: Provided on signup
- Reset: Daily at 00:00 UTC
- No charges for bookings

### Debugging Tools

- Request ID tracking
- Detailed error responses
- Request/response logging
- Performance metrics

## 📊 Response Formats

### Successful Response

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "request_id": "req_123abc",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required parameter: destination",
    "details": {
      "field": "destination",
      "reason": "required"
    }
  },
  "meta": {
    "request_id": "req_456def",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

## 🌟 Featured Integrations

### Popular Use Cases

#### Travel Agencies

- White-label booking platform
- Custom travel planning tools
- Client management systems
- Revenue optimization

#### Corporate Travel

- Expense management integration
- Policy enforcement
- Approval workflows
- Reporting dashboards

#### Content Creators

- Travel blog automation
- Social media integration
- Itinerary visualization
- SEO optimization

## 🆘 Getting Help

### Resources

- **📖 [Full Documentation](https://docs.tripsage.ai)** - Complete guides
- **💬 [Developer Discord](https://discord.gg/tripsage-dev)** - Community support
- **📧 [API Support](mailto:api@tripsage.ai)** - Technical help
- **🎥 [Video Tutorials](https://youtube.com/@tripsage-dev)** - Visual learning

### Support Levels

#### Community Support

- Discord community
- Stack Overflow tag: `tripsage-api`
- GitHub discussions

#### Developer Support

- Email response within 24h
- Code review assistance
- Integration guidance

#### Enterprise Support

- Dedicated Slack channel
- Phone support
- Custom training
- SLA guarantees

## 🚀 What's New

### Recent Updates (v1.5.0)

- 🆕 GraphQL API (Beta)
- 🆕 Batch operations support
- 🆕 Webhook event filtering
- 🔧 Improved error messages
- ⚡ 30% faster response times

### Coming Soon

- 📱 Mobile SDKs (iOS/Android)
- 🌐 More language SDKs
- 🤖 AI model selection
- 📊 Advanced analytics API
- 🔐 OAuth provider support

---

**Ready to build?** Start with our [Usage Examples](usage-examples.md) or dive into the [REST API Reference](../06_API_REFERENCE/REST_API_ENDPOINTS.md)!

> Questions? Join our [Developer Discord](https://discord.gg/tripsage-dev) or email [api@tripsage.ai](mailto:api@tripsage.ai)
