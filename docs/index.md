# TripSage AI API Documentation

Welcome to the official API documentation for **TripSage AI**, an AI-powered travel planning system that integrates multiple data sources to provide comprehensive travel recommendations and itineraries.

## What is TripSage AI?

TripSage AI is a sophisticated travel planning platform that leverages artificial intelligence to:

- **Multi-source Data Integration**: Combines flight data, hotel information, activities, and user preferences
- **Personalized Recommendations**: Uses AI to suggest optimal travel options based on your needs
- **Real-time Updates**: Provides live pricing, availability, and travel alerts
- **Collaborative Planning**: Enables group trip planning with shared itineraries

## Documentation Overview

This documentation site provides everything you need to integrate with the TripSage AI API:

### [Getting Started](api/README.md)

- [API Overview](api/README.md) - Learn about the API structure and capabilities
- [Authentication](api/auth.md) - Set up authentication and API keys
- [Quick Start](api/usage-examples.md) - Code examples to get you running quickly

### [API Reference](api/rest-endpoints.md)

- [REST Endpoints](api/rest-endpoints.md) - Complete REST API reference
- [WebSocket API](api/websocket-realtime-api.md) - Real-time communication
- [Dashboard API](api/dashboard-api.md) - Administrative endpoints
- [Error Codes](api/error-codes.md) - Error handling reference

### [Interactive API](openapi.md)

- Full OpenAPI 3.0 specification
- Interactive API explorer
- Client SDK generation

### [Code Reference](reference/)

- Auto-generated API documentation from source code
- Complete module and class references

## 🔧 Development Setup

### Prerequisites

- Python 3.13+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (for local development)

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/tripsage-ai/tripsage-ai.git
cd tripsage-ai

# Install Python dependencies
uv sync

# Install documentation dependencies
uv sync --group docs

# Start the development environment
docker-compose up -d

# Run the API server
uv run python -m tripsage.api.main

# Build documentation (in another terminal)
mkdocs serve
```

### API Endpoints

- **API Server**: `http://localhost:8000`
- **Documentation**: `http://localhost:8001`
- **Frontend**: `http://localhost:3000`

## Key Concepts

### Authentication

The API uses JWT-based authentication with Supabase integration. All requests require a valid Bearer token.

### Rate Limiting

API calls are rate-limited to prevent abuse. Check the response headers for rate limit information.

### WebSocket Real-time Updates

For real-time features like live pricing updates and collaborative planning, use the WebSocket API.

### Error Handling

All errors follow a consistent JSON format with appropriate HTTP status codes.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details on:

- Reporting bugs
- Requesting features
- Submitting pull requests
- Code style guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 📞 Support

- **Documentation Issues**: [GitHub Issues](https://github.com/tripsage-ai/tripsage-ai/issues)
- **API Support**: [Support Forum](https://github.com/tripsage-ai/tripsage-ai/discussions)
- **Security Issues**: [security@tripsage.ai](mailto:security@tripsage.ai)

---

!!! tip "Need Help?"
Can't find what you're looking for? Check the [FAQ](faq.md) or [contact support](support.md).
