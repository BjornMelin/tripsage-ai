# ADR-0002: Adopt Supabase as Primary Database and Auth Platform

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-06-17
**Category**: platform
**Domain**: Supabase

## Context

TripSage needs a robust, scalable database solution that can handle:

- User authentication and authorization
- Complex relational data (users, trips, bookings, preferences)
- Vector embeddings for AI-powered search and recommendations
- Real-time updates for collaborative features
- Row-level security for multi-tenant data isolation

Additionally, our authentication research revealed critical security vulnerabilities in our custom JWT implementation, with hardcoded fallback secrets representing a CVSS 10.0 vulnerability.

## Decision

We will use Supabase as our primary platform for:

1. **PostgreSQL Database**: Core data storage with pgvector extension
2. **Authentication**: Supabase Auth for secure user management
3. **Real-time**: Built-in real-time subscriptions
4. **Storage**: File storage for user uploads
5. **Edge Functions**: Serverless compute for data processing

We will specifically migrate from custom JWT authentication to Supabase Auth immediately.

## Consequences

### Positive

- **Security**: Eliminates critical JWT vulnerability; automatic security updates
- **Cost Effective**: Free up to 50,000 MAUs; saves ~$90,000 over 5 years vs custom auth
- **Feature Complete**: MFA, OAuth, magic links, session management out-of-box
- **Developer Experience**: Excellent SDKs, auto-generated APIs, TypeScript support

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.
- **Integration**: Row Level Security (RLS) provides automatic data isolation
- **Open Source**: Can self-host if needed; not locked to cloud service

### Negative

- **Vendor Dependency**: Reliance on Supabase infrastructure and pricing
- **Learning Curve**: Team needs to learn Supabase-specific patterns
- **Migration Effort**: Existing data and auth flows need migration
- **Customization Limits**: Some advanced auth scenarios may be constrained

### Neutral

- Changes our infrastructure from self-managed to managed service
- Requires updating all database interactions to use Supabase client
- Need to implement RLS policies for all tables

## Alternatives Considered

### Custom PostgreSQL + JWT Auth

Self-hosted PostgreSQL with custom authentication layer.

**Why not chosen**:

- Security risk of custom JWT implementation
- High maintenance burden (~$19,000/year)
- Missing critical features (MFA, OAuth)
- 2-4 weeks to properly secure vs 2-3 days for Supabase

### Firebase

Google's Backend-as-a-Service platform.

**Why not chosen**:

- NoSQL doesn't fit our relational data model
- More expensive at scale
- Less flexibility for complex queries
- No native pgvector support

### AWS RDS + Cognito

Amazon's managed PostgreSQL and authentication services.

**Why not chosen**:

- More complex setup and integration
- Higher operational overhead
- More expensive for our use case
- Requires managing multiple services

## References

- [Authentication Research Report](../10_RESEARCH/auth/authentication-research-report-2025.md)
- [Supabase Auth Implementation PRD](../10_RESEARCH/auth/supabase-auth-implementation-prd.md)
- [Database Architecture](../03_ARCHITECTURE/DATABASE_ARCHITECTURE.md)
- [Supabase Production Setup Guide](../01_GETTING_STARTED/SUPABASE_PRODUCTION_SETUP.md)
