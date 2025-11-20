# TripSage Database Architecture

## Overview

TripSage uses a unified Supabase PostgreSQL architecture with integrated extensions for all data persistence needs, eliminating complex multi-database patterns while supporting real-time features and vector operations.

## Documentation Index

### Core Database Architecture

- **[Data Architecture](../data-architecture.md)** - Database design patterns, storage decisions, and vector search optimization
- **[Supabase Canonical Schema](supabase-schema.md)** - Single source of truth schema design and migration strategy
- **[Supabase Integration](supabase-integration.md)** - Authentication, SSR patterns, and client configurations
- **[Supabase Operations](supabase-operations.md)** - Webhooks, real-time features, and operational patterns

### Specialized Components

- **[Storage Architecture](../storage-architecture.md)** - File storage, bucket organization, and security patterns
- **[Calendar Service](../calendar-service.md)** - Google Calendar integration and time service patterns

## Quick Start Tasks

| Task | Documentation | Time Estimate |
|------|----------------|----------------|
| Schema setup | [Canonical Schema](supabase-schema.md) | 15-30 min |
| Auth integration | [Supabase Integration](supabase-integration.md) | 30-45 min |
| Webhooks config | [Supabase Operations](supabase-operations.md) | 20-30 min |

## Key Components

- **Supabase PostgreSQL**: Primary database with extensions
- **pgvector**: Vector similarity search for embeddings
- **Vault**: Encrypted API key storage
- **Realtime**: Live data synchronization
- **Storage**: File attachment management

## Architecture Principles

### 1. Unified Data Architecture

Single source of truth with Supabase PostgreSQL, eliminating complex multi-database patterns while supporting real-time features and vector operations.

### 2. Schema-First Design

All data models defined in canonical schema with automatic TypeScript type generation and runtime validation.

### 3. Security by Design

Row Level Security (RLS) policies, encrypted API key storage via Vault, and secure SSR patterns.

### 4. Real-time First

Supabase Realtime for live collaboration, automatic UI updates, and real-time data synchronization.

## Related Documentation

- **[Operators Database](../operators/database/)** - Database operations and Supabase configuration
- **[Developers](../developers/)** - Implementation details and database client usage
- **[API Reference](../api/)** - REST and Realtime API specifications
