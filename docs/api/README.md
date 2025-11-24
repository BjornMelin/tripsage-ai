# TripSage API Documentation

FastAPI-based REST API for the TripSage travel planning platform. **Legacy notice:** The Python/FastAPI backend has been removed in favor of Next.js 16 server route handlers (TypeScript). This document is retained for historical reference; current APIs live in `frontend/src/app/api/**` (see superseded specs SPEC-0007 and SPEC-0010).

## Quick Start

### Development Environment

```bash
# Start the API server
uv run python -m tripsage.api.main

# API available at:
# - Main API: http://localhost:8000
# - Documentation: http://localhost:8000/docs
# - Alternative docs: http://localhost:8000/redoc
```

### First API Call

```bash
# Health check (no auth required)
curl http://localhost:8000/api/health

# Response:
# {"status": "healthy", "timestamp": "...", "version": "1.0.0"}
```

## API Reference

### Complete API Reference

**[API Reference](api-reference.md)** - Complete endpoint documentation with request/response examples

### Supporting Documentation

| Document | Description |
|---|---|
| **[Realtime Guide](realtime-api.md)** | Supabase Realtime private channels |
| **[Error Codes](error-codes.md)** | Error handling and troubleshooting |

## Development

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Testing

```bash
# Run API tests
uv run pytest tests/unit/tripsage/api/ --cov=tripsage.api

# Run integration tests
uv run pytest tests/integration/api/
```
