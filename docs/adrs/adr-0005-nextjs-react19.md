# ADR-0005: Next.js 15 with React 19 for Frontend

**Date**: 2025-06-17

## Status

Accepted

## Context

TripSage's frontend needs to provide a sophisticated AI agent interface with:

- Real-time updates and streaming responses
- Complex interactive visualizations
- Excellent performance and SEO
- Modern developer experience
- Server-side rendering capabilities
- Progressive enhancement

Based on frontend research, we need a framework that supports the latest React features and provides optimal performance for AI-driven applications.

## Decision

We will use Next.js 15 with React 19 for our frontend application.

This technology stack provides:

- React 19's automatic optimization compiler
- Next.js 15's App Router with streaming SSR
- Built-in performance optimizations (Turbopack)
- Server Components for improved performance
- Excellent TypeScript support
- Integrated routing and API routes

## Consequences

### Positive

- **Performance**: Sub-2s builds with Turbopack, optimized bundles
- **Modern Features**: Access to React 19's concurrent features and compiler
- **Developer Experience**: Hot reload, automatic optimization, great tooling
- **SEO Friendly**: Server-side rendering improves search visibility
- **Type Safety**: First-class TypeScript support
- **Ecosystem**: Large community and extensive component libraries

### Negative

- **Complexity**: App Router paradigm shift requires learning
- **Bleeding Edge**: React 19 is very new, potential for bugs
- **Build Size**: Framework overhead compared to vanilla React
- **Lock-in**: Some Next.js specific patterns and optimizations

### Neutral

- Requires Node.js 18+ for optimal performance
- Different mental model from traditional SPAs
- Server Components change how we think about data fetching

## Alternatives Considered

### Vite + React

Modern build tool with React.

**Why not chosen**:

- Lacks built-in SSR/SSG capabilities
- No integrated routing solution
- Would require assembling many tools manually
- Missing optimizations that Next.js provides out-of-box

### Remix

Full-stack React framework.

**Why not chosen**:

- Smaller ecosystem compared to Next.js
- Less focus on static optimization
- Different philosophy that doesn't align with our needs
- Less mature tooling

### Vue.js/Nuxt

Alternative framework ecosystem.

**Why not chosen**:

- Would require team to learn new framework
- Smaller ecosystem for AI/agent UI patterns
- React 19's features are compelling for our use case
- Less community resources for our specific needs

## References

- [Frontend Implementation Plan 2025](../10_RESEARCH/frontend/comprehensive-implementation-plan-2025.md)
- [Frontend Architecture Review](../10_RESEARCH/frontend/frontend-architecture-review-2025.md)
- [Frontend Development Guide](../04_DEVELOPMENT_GUIDE/FRONTEND_DEVELOPMENT.md)
- [React 19 Documentation](https://react.dev/)
- [Next.js 15 Documentation](https://nextjs.org/)
