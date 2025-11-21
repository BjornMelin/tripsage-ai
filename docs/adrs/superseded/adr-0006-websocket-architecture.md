# ADR-0006 (Superseded): Real-time Communication via WebSockets

**Version**: 1.0.0
**Status**: Superseded (by Supabase Realtime private channels; replaced by ADR-0040)
**Date**: 2025-06-17
**Category**: backend
**Domain**: WebSocket

> This ADR is superseded by our Supabase Realtime Authorization design (private channels + RLS on `realtime.messages`). All custom WebSocket infrastructure has been removed. Clients authenticate via `supabase.realtime.setAuth(access_token)` and join topics such as `user:{sub}` and `session:{uuid}` using `supabase.channel(topic, { config: { private: true } })`.

## Context (Historical)

TripSage requires real-time bidirectional communication for:

- Live agent status updates and progress indicators
- Streaming AI responses as they're generated
- Collaborative trip planning features
- Real-time price updates and availability changes
- Multi-user synchronization

HTTP request/response patterns are insufficient for these real-time, event-driven requirements.

## Decision (Historical)

This section captured a now-deprecated decision to build a custom WebSocket stack. It has been replaced by Supabase Realtime and retained here only for traceability.

The architecture supports:

- Automatic reconnection and connection management
- Room-based broadcasting for collaboration
- Message queuing and delivery guarantees
- Graceful degradation to polling if needed

## Consequences (Historical)

### Positive

- **Real-time Updates**: Sub-100ms latency for agent status changes
- **Bi-directional**: True two-way communication for interactive features
- **Efficiency**: Lower overhead than polling for frequent updates
- **Scalability**: Redis pub/sub enables horizontal scaling
- **Reliability**: Socket.io handles reconnection and fallbacks

### Negative

- **Complexity**: More complex than simple HTTP requests
- **Stateful**: Requires connection state management
- **Debugging**: Harder to debug than REST endpoints
- **Infrastructure**: Requires sticky sessions or Redis for scaling

### Neutral

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.

- Different deployment considerations for WebSocket endpoints
- Requires WebSocket-compatible hosting infrastructure
- Need to handle connection lifecycle events

## Alternatives Considered

### Server-Sent Events (SSE)

One-way real-time communication from server to client.

**Why not chosen**:

- Unidirectional only (server to client)
- Less suitable for interactive features
- Limited browser support compared to WebSockets
- No built-in reconnection handling

### Long Polling

Traditional polling with long-held connections.

**Why not chosen**:

- Higher latency and overhead
- More resource intensive
- Not truly real-time
- Poor mobile battery performance

### GraphQL Subscriptions

GraphQL-based real-time updates.

**Why not chosen**:

- Would require adopting GraphQL for entire API
- Additional complexity for our use case
- Less flexible for arbitrary message types
- Smaller ecosystem for our needs

## References

- [WebSocket Infrastructure Guide](../03_ARCHITECTURE/WEBSOCKET_INFRASTRUCTURE.md)
- [WebSocket API Documentation](../06_API_REFERENCE/WEBSOCKET_API.md)
- [Real-time Collaboration Guide](../06_API_REFERENCE/REAL_TIME_COLLABORATION_GUIDE.md)
- [WebSocket Connection Guide](../06_API_REFERENCE/WEBSOCKET_CONNECTION_GUIDE.md)
