# TripSage Frontend Documentation

Comprehensive documentation for the TripSage AI-powered travel planning frontend application.

## 📋 Documentation Overview

### Core Specifications
- **[Frontend Specifications V2](./frontend_specifications_v2.md)** - Complete technical specifications with validated technology stack
- **[Architecture Diagram](./architecture_diagram.md)** - Visual representation of system architecture
- **[TODO-FRONTEND](./TODO-FRONTEND.md)** - Detailed implementation task list

### Design Documents
- **[UI/UX Design Mockups](./ui_ux_design_mockups.md)** - ASCII mockups of key interfaces

### Integration Guides
- **[Supabase Integration Guide](./supabase_integration_guide.md)** - Authentication, real-time subscriptions, and database operations
- **[Vercel AI SDK Integration Guide](./vercel_ai_sdk_integration_guide.md)** - Streaming chat interfaces and tool calling
- **[MCP SDK Integration Guide](./mcp_sdk_integration_guide.md)** - Model Context Protocol for agent communication
- **[Zod Integration Guide](./zod_integration_guide.md)** - Schema validation patterns
- **[Technical Integration Guide V2](./technical_integration_guide_v2.md)** - Modern integration patterns

### Developer Resources
- **[Quickstart Guide V2](./quickstart_guide_v2.md)** - Get started with development
- **[Vercel Deployment Guide](./vercel_deployment_guide.md)** - Production deployment best practices

## 🚀 Technology Stack (January 2025)

- **Framework**: Next.js 15.1+ (App Router) with React 19
- **Language**: TypeScript 5.5+ with strict mode
- **Bundler**: Turbopack (stable in Next.js 15)
- **Styling**: Tailwind CSS v4 with OKLCH color space
- **Components**: shadcn/ui with Radix UI primitives
- **State Management**: Zustand v5 + TanStack Query v5
- **Forms**: React Hook Form v8 + Zod v3
- **AI/Chat**: Vercel AI SDK v5 with UI Message Streaming Protocol
- **Maps**: Mapbox GL JS v3
- **Charts**: Recharts v2 + Chart.js v4
- **Animation**: Framer Motion v11
- **Database**: Supabase (via MCP abstraction)
- **Real-time**: MCP TypeScript SDK with WebSocket/SSE
- **Testing**: Vitest v2 + React Testing Library + Playwright
- **Deployment**: Vercel with Edge Runtime

## 🏗️ Key Features

1. **AI-Native Chat Interface**
   - Real-time streaming responses
   - Multi-agent conversation visualization
   - Rich content support

2. **Agent Visualization**
   - Real-time agent activity monitoring
   - Interactive flow diagrams
   - Progress tracking

3. **API Key Management**
   - Secure client-side storage
   - Provider configuration
   - Usage analytics

4. **Travel Planning**
   - Interactive maps
   - Budget optimization
   - Weather integration
   - Accommodation search

## 📘 Getting Started

1. **Review Core Documentation**
   - Start with [Frontend Specifications V2](./frontend_specifications_v2.md)
   - Check the [Architecture Diagram](./architecture_diagram.md)
   - Review [TODO-FRONTEND](./TODO-FRONTEND.md) for implementation tasks

2. **Set Up Development**
   - Follow the [Quickstart Guide V2](./quickstart_guide_v2.md)
   - Configure environment variables
   - Install dependencies with `pnpm install`

3. **Integrate Services**
   - Set up [Supabase](./supabase_integration_guide.md) for database/auth
   - Configure [Vercel AI SDK](./vercel_ai_sdk_integration_guide.md) for chat
   - Implement [MCP](./mcp_sdk_integration_guide.md) for agent communication
   - Add [Zod](./zod_integration_guide.md) for validation

4. **Deploy to Production**
   - Follow the [Vercel Deployment Guide](./vercel_deployment_guide.md)
   - Configure environment variables
   - Set up monitoring with Sentry and PostHog

## 🛠️ Architecture Overview

The frontend follows a modern architecture optimized for AI-native applications:

- **App Directory**: Next.js 15 App Router with React Server Components
- **Streaming UI**: Progressive rendering with Suspense boundaries
- **Type Safety**: End-to-end type safety with TypeScript and Zod
- **Real-time**: WebSocket connections for agent communication
- **State Management**: Zustand for client state, TanStack Query for server state

## 📱 MCP Integration

The frontend connects to multiple MCP servers for comprehensive functionality:

- **Supabase MCP**: Database operations
- **Neo4j Memory MCP**: Knowledge graph queries
- **Google Maps MCP**: Location services
- **Weather MCP**: Weather forecasting
- **Duffel Flights MCP**: Flight search
- **Airbnb MCP**: Accommodation search
- **Firecrawl/Crawl4AI MCP**: Web content extraction

## 🎨 Design System

- **Colors**: Modern OKLCH color space for better consistency
- **Typography**: Inter font with system fallbacks
- **Components**: shadcn/ui with customizable Radix UI primitives
- **Animations**: Framer Motion for smooth transitions
- **Icons**: Lucide React for consistent iconography

## 🧪 Testing Strategy

- **Unit Tests**: Vitest for component and utility testing
- **Integration Tests**: React Testing Library for user flows
- **E2E Tests**: Playwright for critical user journeys
- **Visual Tests**: Regression testing for UI consistency

## 🔗 Related Resources

- [Main TODO.md](/TODO.md) - Overall project tasks
- [Implementation Status](/docs/status/implementation_status.md) - Project progress
- [Backend Documentation](/docs/implementation/) - API and agent documentation
- [MCP Abstraction Layer](/tripsage/mcp_abstraction/) - Backend MCP integration

## 🤝 Contributing

When working on the frontend:

1. Follow the established tech stack and patterns
2. Update documentation when making changes
3. Write tests for new features
4. Use semantic commit messages
5. Create focused pull requests

## 📅 Roadmap

- **Q1 2025**: Voice interface, mobile app, PWA capabilities
- **Q2 2025**: Multi-language support, collaborative planning
- **Q3 2025**: AR/VR preview, advanced AI optimization
- **Q4 2025**: Enterprise features, API marketplace

## ⚡ Performance Targets

- Lighthouse score: 90+ on all metrics
- First Contentful Paint: <1.5s
- Time to Interactive: <3s
- Bundle size: <200KB initial

For questions or updates, please refer to the main project documentation or create an issue in the repository.