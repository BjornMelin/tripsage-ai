# TripSage Frontend Documentation

Welcome to the TripSage frontend documentation. This directory contains comprehensive documentation for the v2 architecture of the TripSage AI Travel Application frontend.

## Documentation Structure

### Core Documents

1. **[ARCHITECTURE.md](./ARCHITECTURE.md)**
   - Complete v2 architecture overview
   - Technology stack with versions
   - Design patterns and decisions
   - Security implementation (BYOK)
   - Performance strategies

2. **[TECHNOLOGY_STACK_RECOMMENDATIONS.md](./TECHNOLOGY_STACK_RECOMMENDATIONS.md)**
   - Detailed technology choices
   - Version justifications
   - Integration considerations
   - Cost analysis
   - Future-proofing strategies

3. **[frontend_specifications.md](./frontend_specifications.md)**
   - Technical specifications
   - Implementation patterns
   - Component architecture
   - API integration details
   - Testing strategies

4. **[PAGES_AND_FEATURES.md](./PAGES_AND_FEATURES.md)**
   - Comprehensive page listings
   - Feature descriptions
   - Navigation structure
   - UI component inventory
   - User flow documentation

5. **[MIGRATION_GUIDE_v1_to_v2.md](./MIGRATION_GUIDE_v1_to_v2.md)**
   - Step-by-step migration instructions
   - Breaking changes
   - Common issues and solutions
   - Performance improvements
   - Migration checklist

## Key Technologies (v2)

- **Framework**: Next.js 15.3.1 with App Router
- **UI Library**: React 19.1.0 with Server Components
- **Language**: TypeScript 5.5+ (strict mode)
- **Styling**: Tailwind CSS v4.0 with OKLCH colors
- **Components**: shadcn/ui v3 (canary)
- **State**: Zustand v5.0.4 + TanStack Query v5
- **AI Integration**: Vercel AI SDK v5

## Quick Start

1. **New Developers**: Start with [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Migration**: Follow [MIGRATION_GUIDE_v1_to_v2.md](./MIGRATION_GUIDE_v1_to_v2.md)
3. **Implementation**: Reference [frontend_specifications.md](./frontend_specifications.md)
4. **Technology Decisions**: See [TECHNOLOGY_STACK_RECOMMENDATIONS.md](./TECHNOLOGY_STACK_RECOMMENDATIONS.md)

## Implementation Plan

The implementation plan is tracked in the main project [TODO-FRONTEND.md](../../TODO-FRONTEND.md), which includes:

- 20-week phased implementation
- Detailed task breakdowns
- Code examples
- Success metrics

## Architecture Highlights

### Security-First Design

- BYOK (Bring Your Own Key) implementation
- Envelope encryption on backend
- Auto-clearing forms for sensitive data
- Never store raw API keys in frontend

### AI-Centric Features

- Streaming AI responses with SSE
- Context-aware suggestions
- Natural language search
- Real-time collaboration

### Performance Optimization

- Server Components by default
- Strategic code splitting
- Image optimization
- Edge caching

### Modern Development

- Type-safe throughout
- Component-driven architecture
- Comprehensive testing
- Accessible by design

## Archived Documentation

Previous v1 documentation is archived in the [archived/](./archived/) directory for reference.

## Contributing

When updating documentation:

1. Maintain consistency with v2 architecture
2. Update version numbers when dependencies change
3. Include code examples where helpful
4. Keep security considerations in mind
5. Test all code examples

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React 19 Documentation](https://react.dev)
- [Tailwind CSS v4](https://tailwindcss.com)
- [TanStack Query](https://tanstack.com/query)
- [Zustand](https://zustand-demo.pmnd.rs/)

## Support

For questions or clarifications:

1. Check the documentation thoroughly
2. Review code examples in the repository
3. Consult the development team
4. Open an issue in the repository

---

Last Updated: May 2025
Architecture Version: v2.0
